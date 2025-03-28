from django.contrib.auth.models import AbstractUser
from django.db import models

from api.constants import (EMAIL_MAX_LENGTH, FIRST_NAME_MAX_LENGTH,
                           LAST_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH)


class User(AbstractUser):
    """Расширенная модель пользователя, наследующая от AbstractUser."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    username = models.CharField(
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        verbose_name='Имя пользователя',
    )
    email = models.EmailField(
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        verbose_name='Email'
    )
    first_name = models.CharField(
        'Имя',
        max_length=FIRST_NAME_MAX_LENGTH
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=LAST_NAME_MAX_LENGTH
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        blank=True,
        default=None,
        upload_to='profiles'
    )

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
