from django.shortcuts import get_object_or_404
from djoser import views as djoser_views
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from recipes.models import Subscriptions
from .serializers import UserSerializer, SubscriptionsSerializer


class UserViewSet(djoser_views.UserViewSet):
    """Viewset для пользователя."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Показать профиль текущего пользователя."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, url_path=r'me/avatar',
            permission_classes=(IsAuthenticated,))
    def avatar(self, request):
        """Action для аватара пользователя."""

    @avatar.mapping.put
    def set_avatar(self, request):
        user = get_object_or_404(User, pk=request.user.id)
        serializer = UserSerializer(
            user, data=request.data, partial=True,
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': serializer.data.get('avatar')})

    @avatar.mapping.delete
    def delete_avatar(self, request):
        User.objects.filter(pk=request.user.id).update(avatar=None)
        return Response(status=status.HTTP_204_NO_CONTENT)
    

    @action(detail=True,
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id):
        """Action для подписки/отписки."""

    @subscribe.mapping.post
    def create(self, request, id):
        limit_param = request.query_params.get('recipes_limit')
        serializer = SubscriptionsSerializer(
            data=request.data,
            context={
                'request': request,
                'user_pk': id,
                'limit_param': limit_param,
                'action': 'create'})
        serializer.is_valid(raise_exception=True)
        subs = serializer.save(pk=id)
        return Response(subs.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete(self, request, id):
        serializer = SubscriptionsSerializer(
            data=request.data,
            context={
                'request': request,
                'user_pk': id,
                'action': 'delete'})
        serializer.is_valid(raise_exception=True)
        get_object_or_404(
            Subscriptions,
            user=self.request.user,
            cooker=get_object_or_404(User, pk=id)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
