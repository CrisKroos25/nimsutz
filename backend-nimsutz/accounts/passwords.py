from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def validate_new_password(password, user):
    if not password or password.isspace():
        raise ValidationError("La contraseña no puede estar vacía ni contener solo espacios.")

    validate_password(password, user)
