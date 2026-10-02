# files/storage/__init__.py
from functools import lru_cache
from django.conf import settings
from django.utils.module_loading import import_string


@lru_cache
def get_backend():
    backend_class = import_string(settings.STORAGE_BACKEND_CLASS)
    return backend_class(**settings.STORAGE_BACKEND_CONFIG)