from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Админ-панель для управления объектами модели User."""

    search_fields = ('first_name', 'email')
