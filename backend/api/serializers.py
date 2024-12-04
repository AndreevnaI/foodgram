import re
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
# from rest_framework_simplejwt.tokens import RefreshToken

from .constants import (
    EMAIL_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_REGEX,
)
from .utils import validate_confirmation_code
from recipes.models import (Ingredient, Tag, Recipe, IngredientRecipe,
                            Favorites, ShoppingList, User)
from users.serializers import UserSerializer


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


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""

    author = UserSerializer()
    image = Base64ImageField()
    tags = TagSerializer(
        many=True,
        read_only=True)
    ingredients = IngredientRecipeSerializer(
        many=True,
        source='ingredient_in_recipe',
        read_only=True)
    is_favorited = serializers.BooleanField(default=False, read_only=True)
    is_in_shopping_cart = serializers.BooleanField(
        default=False, read_only=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text', 'ingredients',
                  'tags', 'cooking_time', 'is_favorited',
                  'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return Favorites.objects.filter(recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return ShoppingList.objects.filter(recipe=obj).exists()
        return False


class AddRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe - работа с данными."""

    ingredients = IngredientRecipeSerializer(
        many=True,
        write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('name', 'image', 'text', 'ingredients',
                  'tags', 'cooking_time')

    def validate(self, value):
        ingredients = value
        if not ingredients:
            raise ValidationError(
                'Нужно выбрать ингредиент! Поле не может быть пустым.'
            )
        ingredients_list = []
        for item in ingredients:
            ingredient = get_object_or_404(Ingredient, name=item['id'])
            if ingredient in ingredients_list:
                raise ValidationError(
                    {'ingredients': 'Ингридиенты повторяются!'})
            if int(item['amount']) <= 0:
                raise ValidationError(
                    {'amount': 'Указано некорректное количество!'})
            ingredients_list.append(ingredient)
        return value

    def to_representation(self, instance):
        ingredients = super().to_representation(instance)
        ingredients['ingredients'] = IngredientRecipeSerializer(
            instance.recipe_ingredients.all(), many=True).data
        return ingredients

    def add_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            IngredientRecipe.objects.update_or_create(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        recipe.save()
        self.add_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        self.add_ingredients(ingredients, instance)
        instance.tags.clear()
        instance.tags.set(tags)
        return super().update(instance, validated_data)


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер представления ответа укороченных данных о Рецепте"""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class AuthorRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер для наследования моделей вида Автор и Рецепт"""

    _recipe_added_to: str = None

    class Meta:
        model = None
        fields = ('author', 'recipe')
        read_only_fields = ('author',)

    def validate(self, attrs):
        recipe = attrs['recipe']
        user = self.context['request'].user
        if self.Meta.model.objects.filter(author=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f'Рецепт уже добавлен в {self._recipe_added_to}'
            )
        return attrs

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe, context=self.context
        ).data


class FavoritesSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Favorites."""

    _recipe_added_to = 'избранное'

    class Meta(AuthorRecipeSerializer.Meta):
        model = Favorites


class SignupSerializer(serializers.Serializer):
    """Сериализатор для обработки регистрации пользователей."""

    username = serializers.CharField(
        max_length=USERNAME_MAX_LENGTH, required=True
    )
    email = serializers.EmailField(max_length=EMAIL_MAX_LENGTH, required=True)
    password = serializers.CharField(max_length=128, write_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'password'
        )
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name='first_name',
            last_name='last_name',
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def validate(self, data):
        """
        Проверка уникальности username и email,
        а также ограничений для username.
        """

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
    
    def check(self, data):
        email = data.get('email', None)
        password = data.get('password', None)

        if email is None:
            raise serializers.ValidationError(
                'An email address is required to log in.'
            )

        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )

        user = authenticate(username=email, password=password)

        if user is None:
            raise serializers.ValidationError(
                'A user with this email and password was not found.'
            )

        if not user.is_active:
            raise serializers.ValidationError(
                'This user has been deactivated.'
            )

        return {
            'token': user.token,
        }


class TokenSerializer(serializers.Serializer):
    """Сериализатор для обработки токенов аутентификации."""

    username = serializers.CharField(required=True)
    confirmation_code = serializers.CharField(required=True)

    def validate(self, data):
        username = data.get("username")
        confirmation_code = data.get("confirmation_code")
        user = get_object_or_404(User, username=username)

        if not validate_confirmation_code(user, confirmation_code):
            raise serializers.ValidationError("Неверный код подтверждения")

        return data

    # def create(self, validated_data):
    #     user = get_object_or_404(User, username=validated_data["username"])
    #     token = RefreshToken.for_user(user)
    #     return {
    #         "token": str(token.access_token),
    #     }
