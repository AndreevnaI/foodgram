from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet, TagViewSet, IngredientViewSet, Signup, Token
from users.views import UserViewSet


router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('tags', TagViewSet, basename='tag')
router.register('ingredients', IngredientViewSet, basename='ingredient')

# auth_patterns = [
#     path('signup/', Signup.as_view(), name='signup'),
# ]

urlpatterns = [
    path('', include(router.urls)),
    # path('auth/', include((auth_patterns, 'auth'), namespace='auth')),
    path('signup/', Signup.as_view(), name='signup'),
    path('token/', Token.as_view(), name='token'),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
