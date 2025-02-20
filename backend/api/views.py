import short_url
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from recipes.models import (Ingredient, Recipe, Favorites, ShoppingList,
                            Tag, IngredientRecipe)
from api.serializers import (IngredientSerializer, RecipeSerializer,
                             AddEditRecipeSerializer, ShortRecipeSerializer,
                             TagSerializer, RecipeShowIngredientSerializer)
from api.permissions import IsAuthorOrAdminOrReadOnly
from api.filters import RecipeFilter
from api.paginators import LimitPageNumberPaginator


User = get_user_model()


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """ViewSet для модели Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )

    def get_queryset(self):
        queryset = self.queryset
        name = self.request.query_params.get('name')
        if name is not None:
            queryset = queryset.filter(name__startswith=name)
        return queryset

    def list(self, request):
        serializer = self.serializer_class(self.get_queryset(), many=True)
        return Response(serializer.data)


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    """ViewSet для модели Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)

    def list(self, request):
        serializer = self.serializer_class(self.queryset, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для модели Recipe."""

    queryset = Recipe.objects.all()
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

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShortRecipeSerializer(
            recipe,
            context={'request': request}
        )
        if request.method == 'POST':

            _, created = Favorites.objects.get_or_create(
                user=user,
                recipe=recipe
            )
            if not created:
                return Response(
                    data={'error': 'Этот рецепт уже есть в списке.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                data=serializer.data,
                status=status.HTTP_201_CREATED
            )
        try:
            Favorites.objects.get(user=user, recipe=recipe).delete()
        except Favorites.DoesNotExist:
            return Response(
                data={'error': 'Этого рецепта нет в списке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """Action для списка покупок пользователя."""
        pass

    @shopping_cart.mapping.post
    def add_into_shopping_cart(self, request, pk):
        """Добавляет рецепт в список покупок."""
        serializer = RecipeShowIngredientSerializer(
            data=request.data,
            context={
                'request': request,
                'recipe_pk': pk,
                'action': 'add',
                'model': ShoppingList
            }
        )
        serializer.is_valid(raise_exception=True)
        short_recipe = serializer.save(pk=pk)
        return Response(short_recipe.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, pk):
        """Удаляет рецепт из списка покупок."""
        serializer = RecipeShowIngredientSerializer(
            data=request.data,
            context={
                'request': request,
                'recipe_pk': pk,
                'action': 'delete',
                'model': ShoppingList
            }
        )
        serializer.is_valid(raise_exception=True)
        get_object_or_404(
            ShoppingList,
            user=self.request.user,
            recipe=get_object_or_404(Recipe, pk=pk)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачивание списка покупок."""
        user = request.user
        shopping_cart = ShoppingList.objects.filter(user=user)
        if not shopping_cart.exists():
            return Response(
                {"detail": "В корзине пусто."},
                status=status.HTTP_400_BAD_REQUEST
            )
        shopping_list = {}
        for item in shopping_cart:
            ingredients = IngredientRecipe.objects.filter(recipe=item.recipe)
            for ingredient in ingredients:
                name = ingredient.ingredient.name
                amount = ingredient.amount
                unit = ingredient.ingredient.measurement_unit
                if name in shopping_list:
                    shopping_list[name]["amount"] += amount
                else:
                    shopping_list[name] = {"amount": amount, "unit": unit}
        text = "Список покупок:\n\n"
        for name, data in shopping_list.items():
            text += f"{name} - {data['amount']} {data['unit']}\n"
        response = HttpResponse(text, content_type='text/plain; charset=UTF-8')
        response['Content-Disposition'] = 'attachment; filename="shoplist.txt"'
        return response
