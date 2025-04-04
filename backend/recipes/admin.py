from django.contrib import admin

from .models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                     ShoppingList, Subscription, Tag)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Ingredient."""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Tag."""

    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Recipe."""

    list_display = ('author', 'name', 'pub_date')
    search_fields = ('name',)
    list_filter = ('pub_date', 'author')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('author').prefetch_related(
            'tags',
            'ingredients'
        )


@admin.register(IngredientRecipe)
class IngredientRecipeAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели IngredientRecipe."""

    search_fields = ('name',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Subscriptions."""

    list_display = ('user', 'author')
    list_filter = ('author',)
    search_fields = ('user',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Favorites."""

    list_display = ('user', 'recipe')
    search_fields = ('user',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'recipe')


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели ShoppingList."""

    list_display = ('user', 'recipe')
    search_fields = ('user',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'recipe')
