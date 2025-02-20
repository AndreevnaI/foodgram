from rest_framework import permissions


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """Только авторы могут редактировать. Просмотр доступен всем."""

    def has_permission(self, request, view):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """Разрешает редактирование или удаление автору либо админу."""
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )
