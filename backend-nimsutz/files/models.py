# files/models.py
import uuid

from django.conf import settings
from django.db import models


class Folder(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders"
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subfolders"
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "parent", "name"], name="unique_folder_name_per_location"
            ),
        ]

    def __str__(self):
        return self.name


class File(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        AVAILABLE = "available", "Available"
        TRASHED = "trashed", "Trashed"
        DELETED = "deleted", "Deleted"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files"
    )
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="files")
    storage_key = models.CharField(max_length=255, unique=True)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trashed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Solo aplica a archivos "visibles" — uno en trashed/deleted no bloquea
            # el nombre. Ver RN-E3-15 vs RN-E3-29.
            models.UniqueConstraint(
                fields=["folder", "original_name"],
                condition=models.Q(status__in=["uploading", "available"]),
                name="unique_visible_file_name_per_folder",
            ),
        ]

    def __str__(self):
        return self.original_name

    @staticmethod
    def generate_storage_key(owner_id, original_name):
        extension = ""
        if "." in original_name:
            extension = "." + original_name.rsplit(".", 1)[-1].lower()
        return f"{owner_id}/{uuid.uuid4().hex}{extension}"


class QuotaReservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        RELEASED = "released", "Released"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quota_reservations"
    )
    file = models.ForeignKey(
        File, null=True, blank=True, on_delete=models.SET_NULL, related_name="reservations"
    )
    reserved_bytes = models.BigIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()