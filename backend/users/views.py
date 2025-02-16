from django.shortcuts import get_object_or_404
from djoser import views as djoser_views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from recipes.models import Subscriptions
from .serializers import (UserSerializer, UserSubscriptionsSerializer,
                          SubscriptionSerializer)
from api.paginators import LimitPageNumberPaginator
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
)


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
        return Response({'avatar': serializer.data.get('avatar')},
                        status=HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляние аватара текущего пользователя."""
        User.objects.filter(pk=request.user.id).update(avatar=None)
        return Response(status=HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        """Список подписок."""
        users = User.objects.filter(followed__user=request.user)
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
        subs = serializer.save(pk=id)
        return Response(subs.data, status=HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unfollow(self, request, id):
        """Отписка."""
        serializer = SubscriptionSerializer(
            data=request.data,
            context={
                'request': request,
                'user_pk': id,
                'action': 'unfollow'})
        serializer.is_valid(raise_exception=True)
        get_object_or_404(
            Subscriptions,
            user=self.request.user,
            author=get_object_or_404(User, pk=id)).delete()
        return Response(status=HTTP_204_NO_CONTENT)
