from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админ-панель для управления объектами модели User."""

    search_fields = ('name', 'email')
