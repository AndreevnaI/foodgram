from django.shortcuts import get_object_or_404
from djoser import views as djoser_views
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from recipes.models import Subscriptions
from .serializers import UserSerializer, UserSubscriptionsSerializer
from api.paginators import LimitPageNumberPaginator
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
)


class UserViewSet(djoser_views.UserViewSet):
    """Viewset для пользователя."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = LimitPageNumberPaginator

    @action(detail=False, methods=('get',), permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Показывает профиль текущего аутентифицированного пользователя."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(detail=False, url_path=r'me/avatar', permission_classes=(IsAuthenticated,))
    def avatar(self, request):
        """Управление аватаром пользователя."""
        pass

    @avatar.mapping.put
    def set_avatar(self, request):
        """Добавление аватара пользователю."""
        user = get_object_or_404(User, pk=request.user.id)
        serializer = UserSerializer(
            user, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': serializer.data.get('avatar')}, status=HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляет аватар текущего пользователя."""
        User.objects.filter(pk=request.user.id).update(avatar=None)
        return Response(status=HTTP_204_NO_CONTENT)

    @action(detail=True, permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """Операции со списком покупок (добавление/удаление)."""
        pass

    @action(detail=False, permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Список подписок."""
        subscribtions = self.queryset.filter(
            follower__user=self.request.user
        )
        page = self.paginate_queryset(subscribtions)
        serializer = UserSubscriptionsSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
