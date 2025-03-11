from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Админ-панель для управления объектами модели User."""

    list_display = (
        'email',
        'first_name',
        'last_name',
        'username',
        'avatar'
    )
    list_filter = ('is_active', 'is_superuser')
    search_fields = ('first_name', 'last_name', 'username', 'email')
