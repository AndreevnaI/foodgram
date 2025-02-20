import re
from django.contrib.auth import get_user_model
from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .constants import (USERNAME_REGEX)
from recipes.models import (Ingredient, Tag, Recipe, IngredientRecipe,
                            Favorites, ShoppingList, RecipeTag)


User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('__all__')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = ('__all__')


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


class RecipeShowIngredientSerializer(serializers.Serializer):
    """
    Сериализатор для IngredientRecipe (представление ингриента для рецепта).
    """

    def validate(self, data):
        user = self.context['request'].user
        recipe_id = self.context.get('recipe_pk')
        model = self.context.get('model')
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if not recipe:
            raise serializers.ValidationError('Такого рецепта не существует!')
        recipe_filt = model.objects.filter(user=user, recipe=recipe)
        if self.context.get('action') == 'add':
            if recipe_filt:
                raise serializers.ValidationError('Рецепт уже есть!')
        if self.context.get('action') == 'delete':
            if not recipe_filt:
                raise serializers.ValidationError('Для удаления нет рецепта!')
        return data

    def create(self, validated_data):
        model = self.context.get('model')
        recipe = get_object_or_404(Recipe, pk=validated_data.get('pk'))
        model.objects.create(
            user=self.context['request'].user,
            recipe=recipe)
        return ShortRecipeSerializer(recipe)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Ингредиент в рецепте -- используется при создании."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        write_only=True,
        min_value=1,
        max_value=333333)

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
        return self.get_is_recipe(obj, Favorites)

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
        tag_ids = set([tag.id for tag in tags])
        RecipeTag.objects.bulk_create([
            RecipeTag(recipe_id=recipe.id, tag_id=tag_id) for tag_id in tag_ids
        ])

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
        recipe.save()
        return recipe

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
        username = data.get("username")
        email = data.get("email")
        if not re.fullmatch(USERNAME_REGEX, username):
            raise serializers.ValidationError(
                "Содержимое поля 'username' не соотвествует формату."
            )
        if (
            User.objects.filter(email=email).exists()
            and not User.objects.filter(username=username).exists()
        ):
            raise serializers.ValidationError("Данный email уже используется.")
        if (
            User.objects.filter(username=username).exists()
            and not User.objects.filter(email=email).exists()
        ):
            raise serializers.ValidationError(
                "Такой пользователь уже существует."
            )
        return data
