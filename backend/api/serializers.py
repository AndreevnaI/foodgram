import re
import base64
from django.core.files.base import ContentFile
from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer
from djoser.serializers import UserSerializer as DjangoUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .constants import (USERNAME_REGEX)
from recipes.models import (Ingredient, Tag, Recipe, IngredientRecipe,
                            Favorite, ShoppingList, Subscription)
from users.models import User


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для IngredientRecipe."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер представления ответа укороченных данных о Рецепте."""

    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeShowIngredientSerializer(serializers.ModelSerializer):
    """Представление ингриента для рецепта."""

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Ингредиент в рецепте -- используется при создании."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class AuthorSerializer(serializers.ModelSerializer):
    """Сериализатор для кастомной модели User."""

    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.follower.filter(author=obj).exists()
        return False

    def get_avatar(self, data):
        request = self.context.get('request')
        if data.avatar:
            return request.build_absolute_uri(data.avatar.url)
        return None


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""

    author = AuthorSerializer()
    tags = TagSerializer(many=True,)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text', 'ingredients',
                  'tags', 'cooking_time', 'is_favorited',
                  'is_in_shopping_cart')

    def get_is_recipe(self, obj, model):
        if request := self.context.get('request'):
            user = request.user
            if user.is_anonymous:
                return False
            return model.objects.filter(
                user=user, recipe=obj).exists()
        return False

    def get_is_favorited(self, obj):
        return self.get_is_recipe(obj, Favorite)

    def get_is_in_shopping_cart(self, obj):
        return self.get_is_recipe(obj, ShoppingList)

    def get_ingredients(self, obj):
        return obj.ingredients.values('id', 'name', 'measurement_unit',
                                      amount=F('ingredientrecipe__amount')
                                      )


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ShoppingList."""

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingList.objects.all(),
                fields=('user', 'recipe'),
                message='Вы уже добавили рецепт в список покупок',
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return ShortRecipeSerializer(instance.recipe, context=context).data


class AddEditRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe - работа с данными."""

    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault())
    ingredients = IngredientRecipeSerializer(
        many=True,
        required=True,
        write_only=True,
        allow_null=False,
        allow_empty=False,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
        allow_null=False,
        allow_empty=False,
    )
    image = Base64ImageField(required=True, allow_null=False)
    name = serializers.CharField(required=True, max_length=256)
    cooking_time = serializers.IntegerField(
        max_value=32000, min_value=1)

    class Meta:
        model = Recipe
        fields = ('name', 'image', 'text', 'ingredients',
                  'tags', 'cooking_time', 'author')

    def validate(self, data):
        if 'tags' not in data:
            raise serializers.ValidationError(
                'Заполни теги!')
        if 'ingredients' not in data:
            raise serializers.ValidationError(
                'Укажи ингредиенты!')
        tags = data.get('tags')
        tags_list = [tag.id for tag in tags]
        if len(tags_list) != len(set(tags_list)):
            raise serializers.ValidationError(
                'Рецепт содержит повторяющиеся теги!'
            )
        ingredients = data.get('ingredients')
        ingredients_list = [item.get('ingredient').id for item in ingredients]
        if len(ingredients_list) != len(set(ingredients_list)):
            raise serializers.ValidationError(
                'Рецепт содержит повторяющиеся ингредиенты!'
            )
        return data

    def validate_image(self, data):
        if not data:
            raise serializers.ValidationError(
                'Необходимо заполнить поле с картинкой'
            )
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.create_tags(tags, recipe)
        self.create_ingredients(ingredients, recipe)
        recipe.save()
        return recipe

    def create_tags(self, tags, recipe):
        recipe.tags.add(*tags)

    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=dict(ingredient).get('ingredient'),
                amount=dict(ingredient).get('amount')
            ) for ingredient in ingredients
        ])

    def update(self, instance, validated_data):
        recipe = instance
        recipe.tags.clear()
        recipe.ingredients.clear()
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        self.create_tags(tags, recipe)
        self.create_ingredients(ingredients, recipe)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(instance).data


class SignupSerializer(UserCreateSerializer):
    """Сериализатор для обработки регистрации пользователей."""

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'password')

    def validate(self, data):
        """Проверка уникальности username и email"""
        username = data.get('username')
        if not re.fullmatch(USERNAME_REGEX, username):
            raise serializers.ValidationError(
                'Содержимое поля "username" не соотвествует формату.'
            )
        return data


class Base64ImageField(serializers.ImageField):
    """Сериализатор для преобразования аватарки."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_, imgstr = data.split(';base64,')
            ext = format_.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)

    class Meta:
        model = User
        fields = ('avatar',)


class SubscriptionSerializer(serializers.Serializer):
    """Для валидации и создания подписки."""

    def validate(self, data):
        user = self.context['request'].user
        author_data = self.context.get('user_pk')
        author_pk = get_object_or_404(User, pk=author_data)
        subscription = user.follower.filter(author=author_pk)
        action = self.context.get('action')

        if action == 'unfollow':
            if not subscription:
                raise serializers.ValidationError(
                    'Невозможно отписаться, данной подписки не существует!',
                )

        if action == 'follow':
            if user == author_pk:
                raise serializers.ValidationError(
                    'Невозможно подписаться на самого себя!',
                )
            if Subscription.objects.filter(
                    author=author_pk,
                    user=user).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого пользователя!',
                )
        return data

    def create(self, validated_data):
        limit_param = self.context.get('limit_param')
        subscription = get_object_or_404(User, pk=validated_data.get('pk'))
        Subscription.objects.create(
            user=self.context['request'].user,
            author=subscription)
        return UserSubscriptionsSerializer(
            subscription,
            context={'limit_param': limit_param})


class UserSubscriptionsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Subscriptions."""

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        if request := self.context.get('request'):
            if request.user.is_anonymous:
                return False
            return request.user.follower.filter(author=obj).exists()
        return False

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        if limit_param := self.context.get('limit_param'):
            recipes = recipes[:int(limit_param)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data


class UserSerializer(DjangoUserSerializer):
    """Сериализатор для кастомной модели User."""

    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed'
        )

    def validate(self, data):
        request = self.context.get('request')
        if request and request.method == 'PUT':
            if not data.get('avatar'):
                raise serializers.ValidationError(
                    'Не заполенено поле аватара!'
                )
        return data

    def get_avatar(self, data):
        request = self.context.get('request')
        if data.avatar:
            return request.build_absolute_uri(data.avatar.url)
        return None

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.follower.filter(author=obj).exists()
        return False


class FavoriteSerializer(serializers.Serializer):
    """Сериализатор для добавления рецепта в избранное."""

    def create(self, validated_data):
        model = self.context.get('model')
        recipe = get_object_or_404(Recipe, pk=validated_data.get('pk'))
        model.objects.create(
            user=self.context['request'].user,
            recipe=recipe
        )
        return ShortRecipeSerializer(recipe)
