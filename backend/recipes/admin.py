from django.contrib import admin

from .models import (Ingredient, Tag, Recipe, IngredientRecipe, Subscriptions,
                     Favorites, ShoppingList)


class DisplayModelAdmin(admin.ModelAdmin):
    """Display all fields for any model."""

    def __init__(self, model, admin_site):
        """For the list display."""
        self.list_display = [
            field.name for field in model._meta.fields if field.name != 'id'
        ]
        super().__init__(model, admin_site)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Ingredient."""

    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Tag."""

    list_display = ('name', 'slug')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Recipe."""

    list_display = ('author', 'name', 'pub_date')
    search_fields = ('name',)
    list_filter = ('pub_date', 'author', 'name')


@admin.register(IngredientRecipe)
class IngredientRecipeAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели IngredientRecipe."""

    search_fields = ('name',)


@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Subscriptions."""

    list_display = ('user', 'author')
    list_filter = ('author',)
    search_fields = ('user',)


@admin.register(Favorites)
class FavoritesAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели Favorites."""

    list_display = ('user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user',)


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели ShoppingList."""

    list_display = ('user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user',)
