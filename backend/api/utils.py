from django.contrib.auth.tokens import default_token_generator


def generate_confirmation_code(user):
    """Генерирует код подтверждения с помощью токен-генератора Django."""
    return default_token_generator.make_token(user)


def validate_confirmation_code(user, code):
    """Проверка кода подтверждения на соответствие сгенерированному токену."""
    return default_token_generator.check_token(user, code)
