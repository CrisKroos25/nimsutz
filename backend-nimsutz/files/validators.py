"""Reglas compartidas para los nombres de carpetas de la API y los servicios."""
from django.core.exceptions import ValidationError
from django.core.validators import ProhibitNullCharactersValidator

from .models import Folder


def normalize_folder_name(value):
    if not isinstance(value, str):
        raise ValidationError("El nombre debe ser texto.")
    name = value.strip()
    if not name:
        raise ValidationError("El nombre no puede estar vacío.")
    limit = Folder._meta.get_field("name").max_length
    if len(name) > limit:
        raise ValidationError(f"El nombre no puede superar los {limit} caracteres.")
    ProhibitNullCharactersValidator()(name)
    return name
