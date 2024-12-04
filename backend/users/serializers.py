from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from rest_framework import serializers

from .models import User
from recipes.models import Subscriptions, Recipe


User = get_user_model()


class UserSerializer(UserSerializer):
    """Сериализатор для кастомной модели User."""

    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            "avatar",
            'is_subscribed',
        )
        # extra_kwargs = {"password": {"write_only": True}}

    # def create(self, validated_data):
    #     user = User(
    #         email=validated_data['email'],
    #         username=validated_data['username'],
    #         first_name=validated_data['first_name'],
    #         last_name=validated_data['last_name'],
    #     )
    #     user.set_password(validated_data['password'])
    #     user.save()
    #     return user

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if not user.is_anonymous:
            return Subscriptions.objects.filter(user=user, author=obj).exists()
        return False
    
    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar:
            return request.build_absolute_uri(obj.avatar.url)
        return None


class SubscriptionsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Subscriptions."""

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscriptions
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

    def get_recipes(self, obj):
        request = self.context.get('request')
        if request.GET.get('recipe_limit'):
            recipe_limit = int(request.GET.get('recipe_limit'))
            queryset = Recipe.objects.filter(
                author=obj.author)[:recipe_limit]
        else:
            queryset = Recipe.objects.filter(
                author=obj.author)
        serializer = recipes.serializers.ShortRecipeSerializer(
            queryset, read_only=True, many=True
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
