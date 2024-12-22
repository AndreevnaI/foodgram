from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from rest_framework import serializers

from .models import User
from recipes.models import Subscriptions, Recipe


from django.db.models import F
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework.validators import UniqueTogetherValidator
from django.core.files.base import ContentFile
from drf_extra_fields.fields import Base64ImageField



from rest_framework import serializers

from recipes.models import (Tag, Ingredient, Recipe,
                            Favorites)

import base64
from djoser.serializers import UserSerializer, UserCreateSerializer
from api.serializers import ShortRecipeSerializer

class UserSerializer(UserSerializer):
    """Сериализатор для кастомной модели User."""

    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )
    avatar = serializers.SerializerMethodField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )


    def get_is_subscribed(self, data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return data.followed.filter(user=request.user).exists()
        return False

    def get_avatar(self, data):

        request = self.context.get("request")
        if data.avatar:
            return request.build_absolute_uri(data.avatar.url)
        return None

        # if request := self.context.get('request'):
        #     if request.method == 'PUT' and not data:
        #         raise serializers.ValidationError('Выберите фото')
        # return data


class Base64ImageField(serializers.ImageField):
    """"""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_, imgstr = data.split(';base64,')
            ext = format_.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)

    class Meta:
        model = User
        fields = ('avatar',)


class SubscriptionsSerializer(serializers.ModelSerializer):
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

    def validate(self, data):
        author = self.context.get('author')
        user = self.context.get('request').user
        if user == author:
            raise serializers.ValidationError(
                'Невозможно подписаться на самого себя!',
            )
        if Subscriptions.objects.filter(
                author=author,
                user=user).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя!',
            )
        return data

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return Subscriptions.objects.filter(
                user=obj.user,
                author=obj.author).exists()
        return False

    # def get_recipes(self, obj):
    #     request = self.context.get('request')
    #     if request.GET.get('recipe_limit'):
    #         recipe_limit = int(request.GET.get('recipe_limit'))
    #         queryset = Recipe.objects.filter(
    #             author=obj.author)[:recipe_limit]
    #     else:
    #         queryset = Recipe.objects.filter(
    #             author=obj.author)
    #     serializer = recipes.serializers.ShortRecipeSerializer(
    #         queryset, read_only=True, many=True
    #     )
    #     return serializer.data
    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        if limit_param := self.context.get('limit_param'):
            recipes = recipes[:int(limit_param)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
