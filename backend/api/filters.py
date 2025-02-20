from django_filters.rest_framework import FilterSet
from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag
from users.models import User


class RecipeFilter(FilterSet):
    """Фильтр для рецепта."""
    is_favorited = filters.NumberFilter(
        method='get_is_favorited')
    author = filters.ModelChoiceFilter(
        queryset=User.objects.all())
    is_in_shopping_cart = filters.NumberFilter(
        method='get_is_in_shopping_cart')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )

    class Meta:
        model = Recipe
        fields = ('is_favorited', 'author', 'is_in_shopping_cart', 'tags')

    def get_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(shopping_list__user=self.request.user)
        return queryset
