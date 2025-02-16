import re
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from djoser.serializers import UserCreateSerializer
from rest_framework.validators import UniqueTogetherValidator
from django.db.models import F

from .constants import (
    EMAIL_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_REGEX,
)
from .utils import validate_confirmation_code
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
    """Сериалайзер представления ответа укороченных данных о Рецепте"""
    image = Base64ImageField(required=True, allow_null=False)


    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeShowIngredientSerializer(serializers.Serializer):
    """
    Сериализатор для IngredientRecipe (представление ингриента для рецепта).
    """

    # id = serializers.IntegerField(source='ingredient.id')
    # name = serializers.CharField(source='ingredient.name')
    # measurement_unit = serializers.CharField(
    #     source='ingredient.measurement_unit'
    # )

    # class Meta:
    #     model = IngredientRecipe
    #     fields = ('id', 'name', 'measurement_unit', 'amount')

    def create(self, validated_data):
        model = self.context.get('model')
        recipe = get_object_or_404(Recipe, pk=validated_data.get('pk'))
        model.objects.create(
            user=self.context['request'].user,
            recipe=recipe)
        return ShortRecipeSerializer(recipe)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Ингредиент в рецепте -- используется при создании"""
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

        # if request := self.context.get('request'):
        #     if request.method == 'PUT' and not data:
        #         raise serializers.ValidationError('Выберите фото')
        # return data


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
        # user = self.context.get('request').user
        # if not user.is_anonymous:
        #     return Favorites.objects.filter(recipe=obj).exists()
        # return False
        return self.get_is_recipe(obj, Favorites)

    def get_is_in_shopping_cart(self, obj):
        # user = self.context.get('request').user
        # if not user.is_anonymous:
        #     return ShoppingList.objects.filter(recipe=obj, user=user).exists()
        # return False
        return self.get_is_recipe(obj, ShoppingList)

    def get_ingredients(self, obj):
        return obj.ingredients.values('id', 'name', 'measurement_unit',
                                      amount=F('ingredientrecipe__amount')
                                      )


class ShoppingListSerializer(serializers.ModelSerializer):

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
        # ingredients = super().to_representation(instance)
        # ingredients['ingredients'] = IngredientRecipeSerializer(
        #     instance.recipe_ingredients.all(), many=True).data
        # return ingredients
        return RecipeSerializer(instance).data


# class FavoritesSerializer(serializers.ModelSerializer):
#     """Сериализатор для модели Favorites."""

#     _recipe_added_to = 'избранное'

#     class Meta(AuthorRecipeSerializer.Meta):
#         model = Favorites


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


# class SignupSerializer(UserCreateSerializer):
#     """Сериализатор для обработки регистрации пользователей."""

#     class Meta:
#         model = User
#         fields = (
#             'email',
#             'id',
#             'username',
#             'first_name',
#             'last_name',
#             'password'
#         )
#         # extra_kwargs = {"password": {"write_only": True}}

#     def create(self, validated_data):
#         user = User(
#             email=validated_data['email'],
#             username=validated_data['username'],
#             first_name=validated_data['first_name'],
#             last_name=validated_data['last_name'],
#         )
#         user.set_password(validated_data['password'])
#         user.save()
#         return user
