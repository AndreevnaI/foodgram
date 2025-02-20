import base64
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer as DjangoUserSerializer
from rest_framework import serializers

from .models import User
from recipes.models import Subscriptions
from api.serializers import ShortRecipeSerializer


class Base64ImageField(serializers.ImageField):
    """Сериализатор для преобразования аватарки."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_, imgstr = data.split(';base64,')
            ext = format_.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(DjangoUserSerializer):
    """Сериализатор для кастомной модели User."""

    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed'
        )

    def validate(self, data):
        request = self.context.get('request')
        if request and request.method == 'PUT':
            if not data.get('avatar'):
                raise serializers.ValidationError(
                    'Не заполенено поле аватара!'
                )
        return data

    def get_avatar(self, data):
        request = self.context.get('request')
        if data.avatar:
            return request.build_absolute_uri(data.avatar.url)
        return None

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.follower.filter(author=obj).exists()
        return False


class SubscriptionSerializer(serializers.Serializer):
    """Для валидации и создания подписки."""

    def validate(self, data):
        user = self.context['request'].user
        author_data = self.context.get('user_pk')
        author_pk = get_object_or_404(User, pk=author_data)
        subscription = user.follower.filter(author=author_pk)

        if self.context.get('action') == 'unfollow':
            if not subscription:
                raise serializers.ValidationError(
                    'Невозможно отписаться, данной подписки не существует!',
                )

        if self.context.get('action') == 'follow':
            if user == author_pk:
                raise serializers.ValidationError(
                    'Невозможно подписаться на самого себя!',
                )
            if Subscriptions.objects.filter(
                    author=author_pk,
                    user=user).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого пользователя!',
                )
        return data

    def create(self, validated_data):
        limit_param = self.context.get('limit_param')
        subs = get_object_or_404(User, pk=validated_data.get('pk'))
        Subscriptions.objects.create(
            user=self.context['request'].user,
            author=subs)
        return UserSubscriptionsSerializer(
            subs,
            context={'limit_param': limit_param})


class UserSubscriptionsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Subscriptions."""

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        if request := self.context.get('request'):
            if request.user.is_anonymous:
                return False
            return request.user.follower.filter(author=obj).exists()
        return False

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        if limit_param := self.context.get('limit_param'):
            recipes = recipes[:int(limit_param)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
