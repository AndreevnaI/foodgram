import re
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from djoser.serializers import UserCreateSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator
# from rest_framework_simplejwt.tokens import RefreshToken

from .constants import (
    EMAIL_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_REGEX,
)
from .utils import validate_confirmation_code
from recipes.models import (Ingredient, Tag, Recipe, IngredientRecipe,
                            Favorites, ShoppingList)
from users.serializers import UserSerializer


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


class RecipeShowIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для IngredientRecipe (представление ингриента для рецепта).
    """

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер представления ответа укороченных данных о Рецепте"""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


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


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""

    author = UserSerializer()
    tags = TagSerializer(
        many=True,
    )
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


class AddRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe - работа с данными."""

    # author = serializers.HiddenField(
    #     default=serializers.CurrentUserDefault())
    ingredients = IngredientRecipeSerializer(
        many=True,
        required=True,
        write_only=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
    )
    image = Base64ImageField(required=True, allow_null=False)
    # name = serializers.CharField(required=True, max_length=256)
    # cooking_time = serializers.IntegerField(
    #     max_value=32000, min_value=1)

    class Meta:
        model = Recipe
        fields = ('name', 'image', 'text', 'ingredients',
                  'tags', 'cooking_time')

    def validate_ingredients(self, data):
        if 'ingredients' not in data:
            raise ValidationError(
                'Нужно выбрать ингредиент! Поле не может быть пустым.'
            )
        ingredients_list = [item['id'].id for item in data]
        if len(ingredients_list) != len(set(ingredients_list)):
            raise serializers.ValidationError(
                'Ингридиенты повторяются!'
            )
        return data

    def validate_tags(self, data):
        if 'tags' not in data:
            raise ValidationError(
                'Выберите тег.'
            )
        tags_list = [item.id for item in data]
        if len(tags_list) != len(set(tags_list)):
            raise serializers.ValidationError(
                'Теги повторяются!'
            )
        return data

    def add_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            IngredientRecipe.objects.update_or_create(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )

    def add_tags(self, tags, recipe):
        recipe.tags.set(tags)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        user = self.context.get('request').user
        recipe = Recipe.objects.create(**validated_data, author=user)
        self.add_tags(tags, recipe)
        self.add_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        recipe = instance
        recipe.tags.clear()
        recipe.ingredients.clear()
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        self.add_ingredients(recipe, tags, ingredients)
        recipe.save()
        return recipe

    def to_representation(self, instance):
        # ingredients = super().to_representation(instance)
        # ingredients['ingredients'] = IngredientRecipeSerializer(
        #     instance.recipe_ingredients.all(), many=True).data
        # return ingredients
        return RecipeSerializer(instance).data


class AuthorRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер для наследования моделей вида Автор и Рецепт"""


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

#     def validate(self, data):
#         """
#         Проверка уникальности username и email,
#         а также ограничений для username.
#         """

#         username = data.get("username")
#         email = data.get("email")
#         if not re.fullmatch(USERNAME_REGEX, username):
#             raise serializers.ValidationError(
#                 "Содержимое поля 'username' не соотвествует формату."
#             )
#         if (
#             User.objects.filter(email=email).exists()
#             and not User.objects.filter(username=username).exists()
#         ):
#             raise serializers.ValidationError("Данный email уже используется.")
#         if (
#             User.objects.filter(username=username).exists()
#             and not User.objects.filter(email=email).exists()
#         ):
#             raise serializers.ValidationError(
#                 "Такой пользователь уже существует."
#             )
#         return data

#     def check(self, data):
#         email = data.get('email', None)
#         password = data.get('password', None)

#         if email is None:
#             raise serializers.ValidationError(
#                 'An email address is required to log in.'
#             )

#         if password is None:
#             raise serializers.ValidationError(
#                 'A password is required to log in.'
#             )

#         user = authenticate(username=email, password=password)

#         if user is None:
#             raise serializers.ValidationError(
#                 'A user with this email and password was not found.'
#             )

#         if not user.is_active:
#             raise serializers.ValidationError(
#                 'This user has been deactivated.'
#             )

#         return {
#             'token': user.token,
#         }
