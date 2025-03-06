from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели User."""

    search_fields = ('name', 'email')
