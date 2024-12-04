from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from api.constants import (EMAIL_MAX_LENGTH, USERNAME_MAX_LENGTH,
                           USERNAME_REGEX)


class User(AbstractUser):
    """Расширенная модель пользователя, наследующая от AbstractUser."""

    username = models.CharField(
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[
            RegexValidator(
                regex=USERNAME_REGEX,
                message="Имя пользователя может содержать "
                "только буквы, цифры, @, ., +, -, и _.",
            )
        ],
        verbose_name='Имя пользователя',
    )
    email = models.EmailField(
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        verbose_name='Email',
        help_text='Введите адрес электронной почты'
    )
    first_name = models.CharField(
        'Имя',
        max_length=150
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=150
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        blank=True,
        null=True,
        default=None,
        upload_to='profiles'
    )

    class Meta:
        ordering = ("username",)
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username

