import short_url
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser import views as djoser_views
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_204_NO_CONTENT)

from api.filters import IngredientFilter, RecipeFilter
from api.paginators import LimitPageNumberPaginator
from api.permissions import IsAuthorOrAdminOrReadOnly
from api.serializers import (AddEditRecipeSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeSerializer,
                             RecipeShowIngredientSerializer,
                             ShortRecipeSerializer, SubscriptionSerializer,
                             TagSerializer, UserSerializer,
                             UserSubscriptionsSerializer)
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingList, Subscription, Tag)

User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для модели Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (AllowAny, )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ['name']


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для модели Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для модели Recipe."""

    queryset = Recipe.objects.select_related(
        'author').prefetch_related('tags', 'ingredients')
    filter_backends = (DjangoFilterBackend, )
    pagination_class = LimitPageNumberPaginator
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'get_link'):
            return (AllowAny(),)
        return (IsAuthenticated(), IsAuthorOrAdminOrReadOnly())

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AddEditRecipeSerializer
        return RecipeSerializer

    @action(
        detail=True,
        permission_classes=(AllowAny,),
        url_path='get-link'
    )
    def get_link(self, request, pk):
        """Ссылка на рецепт."""
        url = 'http://{}/s/{}/'.format(
            settings.DOMAIN_NAME,
            short_url.encode_url(int(pk))
        )
        return Response({'short-link': url}, status=status.HTTP_200_OK)

    @action(detail=True, permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        """Action для избранного рецепта."""

    @favorite.mapping.post
    def add_to_favorite(self, request, pk):
        """Добавить рецепт в избранное."""
        recipe = get_object_or_404(Recipe, pk=pk).pk
        serializer = FavoriteSerializer(
            data={'user': request.user.pk, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        favorite_recipe = serializer.save(pk=pk)
        short_recipe = ShortRecipeSerializer(favorite_recipe.recipe).data
        return Response(data=short_recipe, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_from_favorite(self, request, pk):
        """Удалить рецепт из избранного."""
        deleted_raws, _ = Favorite.objects.filter(user=request.user,
                                                  recipe=pk).delete()
        if deleted_raws == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """Action для списка покупок пользователя."""

    @shopping_cart.mapping.post
    def add_into_shopping_cart(self, request, pk):
        """Добавляет рецепт в список покупок."""
        recipe = get_object_or_404(Recipe, pk=pk).pk
        serializer = RecipeShowIngredientSerializer(
            data={'user': request.user.pk, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        shopping_list = serializer.save(pk=pk)
        short_recipe = ShortRecipeSerializer(shopping_list.recipe).data
        return Response(data=short_recipe, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, pk):
        """Удаляет рецепт из списка покупок."""
        deleted_raws, _ = ShoppingList.objects.filter(user=request.user,
                                                      recipe__id=pk).delete()
        if deleted_raws == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачивание списка покупок."""
        user = request.user
        ingredient_recipes = IngredientRecipe.objects.filter(
            recipe__shopping_list__user=user).select_related('ingredient')
        shopping_list = {}
        for recipe_ingredient in ingredient_recipes:
            name = recipe_ingredient.ingredient.name
            amount = recipe_ingredient.amount
            unit = recipe_ingredient.ingredient.measurement_unit
            if name in shopping_list:
                shopping_list[name]['amount'] += amount
            else:
                shopping_list[name] = {'amount': amount, 'unit': unit}

        return self.get_shopping_cart_file_response(shopping_list)

    def get_shopping_cart_file_response(self, shopping_list):
        text = 'Список покупок:\n\n'
        for name, data in shopping_list.items():
            text += f"{name} - {data['amount']} {data['unit']}\n"
        response = HttpResponse(text, content_type='text/plain; charset=UTF-8')
        response['Content-Disposition'] = 'attachment; filename="shoplist.txt"'

        return response


class UserViewSet(djoser_views.UserViewSet):
    """Viewset для пользователя."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = LimitPageNumberPaginator

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Показывает профиль текущего аутентифицированного пользователя."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(
        detail=False,
        url_path=r'me/avatar',
        permission_classes=(IsAuthenticated,)
    )
    def avatar(self, request):
        """Управление аватаром пользователя."""

    @avatar.mapping.put
    def set_avatar(self, request):
        """Добавление аватара пользователю."""
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': serializer.data.get('avatar')},
                        status=HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара текущего пользователя."""
        request.user.avatar.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        """Список подписок."""
        users = User.objects.filter(
            followed__user=request.user).annotate(
                recipes_count=Count('recipes'))
        limit_param = request.query_params.get('recipes_limit')
        paginated_queryset = self.paginate_queryset(users)
        serializer = UserSubscriptionsSerializer(
            paginated_queryset,
            context={
                'limit_param': limit_param},
            many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        """Action для подписки/отписки на пользователя."""

    @subscribe.mapping.post
    def follow(self, request, id):
        """Подписка."""
        limit_param = request.query_params.get('recipes_limit')
        serializer = SubscriptionSerializer(
            data=request.data,
            context={
                'request': request,
                'user_pk': id,
                'limit_param': limit_param,
                'action': 'follow'})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save(pk=id)
        return Response(subscription.data, status=HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unfollow(self, request, id):
        """Отписка."""
        deleted_raws, _ = Subscription.objects.filter(user=request.user,
                                                      author=id).delete()
        if deleted_raws == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

