from rest_framework import viewsets, status, mixins
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.decorators import action
from rest_framework.validators import ValidationError
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from djoser.views import UserViewSet

from recipes.models import (Ingredient, Recipe, Favorites, ShoppingList, Tag)
# from users.models import User
from users.serializers import UserSerializer
from api.downloads import shopping_list
from api.serializers import (IngredientSerializer, RecipeSerializer,
                             AddEditRecipeSerializer, ShortRecipeSerializer,
                             TagSerializer, SignupSerializer)
from api.permissions import IsAuthorOrAdminOrReadOnly
from api.filters import IngredientFilter, RecipeFilter
from api.paginators import LimitPageNumberPaginator


User = get_user_model()


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """ViewSet для модели Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (IngredientFilter, )

    def list(self, request):
        serializer = self.serializer_class(self.queryset, many=True)
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
    # permission_classes = (IsAuthorOrAdminOrReadOnly, )
    filter_backends = (DjangoFilterBackend, )
    pagination_class = LimitPageNumberPaginator
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AddEditRecipeSerializer
        return RecipeSerializer

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
            Favorites.objects.create(user=user, recipe=recipe)
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


    # @action(
    #     detail=True,
    #     methods=['POST', 'DELETE'],
    #     permission_classes=[IsAuthenticated]
    # )
    # def shopping_cart(self, request, pk):
    #     user = request.user
    #     recipe = get_object_or_404(Recipe, pk=pk)
    #     serializer = ShortRecipeSerializer(
    #         recipe,
    #         context={'request': request}
    #     )
    #     shopping_list_obj, _ = ShoppingList.objects.get_or_create(
    #         user=user
    #     )
    #     if request.method == 'POST':
    #         ShoppingList.objects.create(
    #             shopping_list=shopping_list_obj,
    #             recipe=recipe
    #         )
    #         return Response(
    #             data=serializer.data,
    #             status=status.HTTP_201_CREATED)
    #     try:
    #         ShoppingList.objects.get(
    #             shopping_list=shopping_list_obj,
    #             recipe=recipe
    #         ).delete()
    #     except ShoppingList.DoesNotExist:
    #         return Response(
    #             data={'error': 'Данный рецепт отсутствует в вашем списке.'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """"""
        pass

    @shopping_cart.mapping.post
    def add_into_shopping_cart(self, request, pk):
        """Добавляет рецепт в список покупок пользователя."""
        serializer = ShortRecipeSerializer(
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

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_list(self, request):
        print('DOWNLOAD_SHOPPING_LIST')
        author = User.objects.get(id=self.request.user.pk)
        if author.shopping_list.exists():
            return shopping_list(self, request, author)
        return Response(status=status.HTTP_404_NOT_FOUND)
    

# class Signup(UserViewSet):
#     """Регистрация пользователя."""

#     permission_classes = (AllowAny,)
#     serializer_class = SignupSerializer

#     def post(self, request):
#         # serializer = SignupSerializer(data=request.data)
#         # serializer.is_valid(raise_exception=True)
#         # username = serializer.validated_data["username"]
#         # email = serializer.validated_data["email"]
#         # user, _ = User.objects.get_or_create(username=username, email=email)
#         # # confirmation_code = generate_confirmation_code(user)
#         # # send_mail(
#         # #     "Confirmation Code",
#         # #     f"Your confirmation code is {confirmation_code}",
#         # #     settings.DEFAULT_FROM_EMAIL,
#         # #     [user.email],
#         # # )
#         # return Response(serializer.data, status=status.HTTP_200_OK)
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()
#         return Response({
#             "user": UserSerializer(user, context=self.get_serializer_context()).data,
#             "message": "Пользователь успешно создан",
#         })
