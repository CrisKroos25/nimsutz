# files/storage/base.py
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """
    Contrato que cualquier backend de almacenamiento debe cumplir.
    services.py solo conoce esta interfaz, nunca boto3 directamente.
    """

    @abstractmethod
    def generate_upload_url(self, *, storage_key, content_type, expires_in=300):
        ...

    @abstractmethod
    def generate_download_url(self, *, storage_key, original_name, expires_in=300):
        ...

    @abstractmethod
    def head_object(self, *, storage_key):
        """Devuelve metadata real del objeto, o None si no existe."""
        ...

    @abstractmethod
    def delete_object(self, *, storage_key):
        ...