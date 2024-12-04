from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.decorators import action
from rest_framework.validators import ValidationError
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from recipes.models import (Ingredient, Recipe, Favorites, ShoppingList, Tag)
from users.models import User
from users.serializers import UserSerializer
from api.downloads import shopping_list
from api.serializers import (IngredientSerializer, RecipeSerializer,
                             AddRecipeSerializer, FavoritesSerializer,
                             TagSerializer, SignupSerializer, TokenSerializer)
from api.permissions import IsAuthorOrAdminOrReadOnly
from api.filters import IngredientFilter, RecipeFilter


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """ViewSet для модели Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (IngredientFilter, )


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    """ViewSet для модели Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для модели Recipe."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly, )
    filter_backends = (DjangoFilterBackend, )
    pagination_class = PageNumberPagination
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        return AddRecipeSerializer

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.add_recipe(Favorites, request, pk)
        else:
            return self.delete_recipe(Favorites, request, pk)

    def add_recipe(self, model, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = self.request.user
        if Favorites.objects.filter(recipe=recipe, user=user).exists():
            raise ValidationError('Рецепт уже добавлен!')
        Favorites.objects.create(recipe=recipe, user=user)
        serializer = FavoritesSerializer(recipe)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    def delete_recipe(self, model, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = self.request.user
        obj = get_object_or_404(model, recipe=recipe, user=user)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            recipe = get_object_or_404(Recipe, id=pk)
            if ShoppingList.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            ShoppingList.objects.create(user=request.user, recipe=recipe)
            serializer = AddRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        cart = ShoppingList.objects.filter(user=request.user, recipe__id=pk)
        if cart.exists():
            cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_list(self, request):
        author = User.objects.get(id=self.request.user.pk)
        if author.shopping_list.exists():
            return shopping_list(self, request, author)
        return Response(status=status.HTTP_404_NOT_FOUND)


class Signup(APIView):
    """Регистрация пользователя."""

    permission_classes = (AllowAny,)
    serializer_class = SignupSerializer

    def post(self, request):
        # serializer = SignupSerializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # username = serializer.validated_data["username"]
        # email = serializer.validated_data["email"]
        # user, _ = User.objects.get_or_create(username=username, email=email)
        # # confirmation_code = generate_confirmation_code(user)
        # # send_mail(
        # #     "Confirmation Code",
        # #     f"Your confirmation code is {confirmation_code}",
        # #     settings.DEFAULT_FROM_EMAIL,
        # #     [user.email],
        # # )
        # return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "message": "Пользователь успешно создан",
        })


class Token(APIView):
    """Получения токена."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_data = serializer.save()
        return Response(token_data, status=status.HTTP_200_OK)
