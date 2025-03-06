from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from api.constants import (NAME_MAX_LENGTH, MEASUREMENT_UNIT_LENGTH,
                           TAG_LENGTH, SLUG_LENGTH, СOOKING_TIME_MIN,
                           СOOKING_TIME_MAX, AMOUNT_INGREDIENT_MIN,
                           AMOUNT_INGREDIENT_MAX)
from users.models import User


class Ingredient(models.Model):
    """Ингредиенты для рецептов."""

    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название ингредиента',
        db_index=True
    )
    measurement_unit = models.CharField(
        max_length=MEASUREMENT_UNIT_LENGTH,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Тэги для рецептов."""

    name = models.CharField(
        max_length=TAG_LENGTH,
        unique=True,
        verbose_name='Название тега',
    )
    slug = models.SlugField(
        max_length=SLUG_LENGTH,
        unique=True,
        verbose_name='Слаг',
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Хранение рецептов."""

    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название рецепта',
        db_index=True
    )
    image = models.ImageField(
        upload_to='media/',
        verbose_name='Картинка рецепта',
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(
                СOOKING_TIME_MIN,
                'Минимальное время приготовления'
            ),
            MaxValueValidator(
                СOOKING_TIME_MAX,
                'Максимальное время приготовления'
            )
        ]
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ('-pub_date',)
        default_related_name = 'recipe'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    """Вспомогательная модель для связи ингридиентов с рецептом."""

    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredients',
        verbose_name='Название рецепта',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                AMOUNT_INGREDIENT_MIN,
                'Минимальное количество ингредиентов'
            ),
            MaxValueValidator(
                AMOUNT_INGREDIENT_MAX,
                'Максимальное количество ингредиентов'
            )
        ],
        verbose_name='Количество',
    )

    class Meta:
        verbose_name = 'Cостав рецепта'
        verbose_name_plural = 'Состав рецептов'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredients'
            )
        ]


class Subscription(models.Model):
    """Подписки на авторов рецептов."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Подписчик',
        related_name='follower'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Подписка',
        related_name='followed'
    )

    class Meta:
        verbose_name = 'Моя подписка'
        verbose_name_plural = 'Мои подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_following'
            )
        ]


class Favorite(models.Model):
    """Избранные рецепты пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Избранные рецепты',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Избранные рецепты'
    )

    class Meta:
        default_related_name = 'favorites'
        verbose_name = 'Избранные рецепты'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorites'
            ),
        ]

    def __str__(self):
        return f'{self.recipe}'


class ShoppingList(models.Model):
    """Список покупок пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_list',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_list',
    )

    class Meta:
        default_related_name = 'shopping_list'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='unique_recipe'
            ),
        ]

    def __str__(self):
        return f'{self.recipe}'
