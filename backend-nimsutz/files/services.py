# files/services.py
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import IntegrityError
from django.db.utils import DataError
from django.utils import timezone
from django.db.models import Sum

from . import storage
from .models import Folder, File, QuotaReservation

# Folder

def create_folder(*, owner, parent, name):
    """
    RN-E3-08 / RN-E3-09 / RN-E3-10 / RN-E3-11: carpeta padre propia (o raíz),
    nombre válido, sin duplicados en la misma ubicación (normalizado).
    """
    normalized_name = name.strip()

    if parent is not None and parent.owner_id != owner.id:
        raise ValidationError("La carpeta padre no pertenece al usuario.")

    exists = Folder.objects.filter(
        owner=owner, parent=parent, name__iexact=normalized_name
    ).exists()
    if exists:
        raise ValidationError("Ya existe una carpeta con ese nombre en esta ubicación.")

    return Folder.objects.create(owner=owner, parent=parent, name=normalized_name)


def rename_folder(*, folder, new_name):
    """RN-E3-14: renombrar vuelve a aplicar las reglas de nombre y duplicidad."""
    normalized_name = new_name.strip()

    exists = (
        Folder.objects.filter(
            owner=folder.owner, parent=folder.parent, name__iexact=normalized_name
        )
        .exclude(pk=folder.pk)
        .exists()
    )
    if exists:
        raise ValidationError("Ya existe una carpeta con ese nombre en esta ubicación.")

    folder.name = normalized_name
    folder.save(update_fields=["name", "updated_at"])
    return folder


def delete_folder(*, folder):
    """RN-E3-13: una carpeta solo puede eliminarse si está vacía."""
    has_subfolders = folder.subfolders.exists()
    has_files = folder.files.exclude(status="deleted").exists()
    if has_subfolders or has_files:
        raise ValidationError("La carpeta no está vacía.")
    folder.delete()

# Files

def get_available_quota(owner):
    """RN-E3-22/23/24: consumo = archivos activos + reservas pendientes (incluye papelera)."""
    used = QuotaReservation.objects.filter(
        owner=owner, status__in=[QuotaReservation.Status.PENDING, QuotaReservation.Status.CONFIRMED]
    ).aggregate(total=Sum("reserved_bytes"))["total"] or 0
    return settings.SIMULATED_QUOTA_BYTES - used


def request_upload(*, owner, folder, original_name, content_type, size_bytes):
    if folder.owner_id != owner.id:
        raise ValidationError("La carpeta no pertenece al usuario.")  # RN-E3-04/05

    if content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise ValidationError("Tipo de archivo no permitido.")  # RN-E3-18

    if size_bytes <= 0 or size_bytes > settings.MAX_FILE_SIZE_BYTES:
        raise ValidationError("El tamaño del archivo excede el límite permitido.")  # RN-E3-17

    normalized_name = original_name.strip()
    name_taken = File.objects.filter(
        folder=folder,
        original_name__iexact=normalized_name,
        status__in=[File.Status.UPLOADING, File.Status.AVAILABLE],
    ).exists()
    if name_taken:
        raise ValidationError("Ya existe un archivo con ese nombre en esta carpeta.")  # RN-E3-15/16

    if get_available_quota(owner) < size_bytes:
        raise ValidationError("Cuota insuficiente para este archivo.")  # RN-E3-25

    storage_key = File.generate_storage_key(owner.id, normalized_name)

    file = File.objects.create(
        owner=owner,
        folder=folder,
        storage_key=storage_key,
        original_name=normalized_name,
        content_type=content_type,
        size_bytes=size_bytes,
        status=File.Status.UPLOADING,
    )

    QuotaReservation.objects.create(
        owner=owner,
        file=file,
        reserved_bytes=size_bytes,
        status=QuotaReservation.Status.PENDING,
        expires_at=timezone.now() + timedelta(minutes=settings.RESERVATION_TTL_MINUTES),
    )

    upload_url = storage.generate_upload_url(
        storage_key=storage_key, content_type=content_type
    )

    return file, upload_url


def confirm_upload(*, file, owner):
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")  # RN-E3-06

    if file.status != File.Status.UPLOADING:
        raise ValidationError("Este archivo ya fue confirmado o ya no está pendiente.")

    reservation = file.reservations.filter(status=QuotaReservation.Status.PENDING).first()
    if reservation is None:
        raise ValidationError("No hay una reserva pendiente para este archivo.")

    metadata = storage.head_object(storage_key=file.storage_key)

    if metadata is None:
        # El cliente nunca completó el PUT contra MinIO.
        reservation.status = QuotaReservation.Status.RELEASED
        reservation.save(update_fields=["status"])
        file.delete()
        raise ValidationError("El archivo no fue subido a almacenamiento.")  # RN-E3-38

    real_size = metadata["ContentLength"]
    if real_size != file.size_bytes:
        # RN-T-08: no se confía en lo declarado, se verifica el contenido real.
        storage.delete_object(storage_key=file.storage_key)
        reservation.status = QuotaReservation.Status.RELEASED
        reservation.save(update_fields=["status"])
        file.delete()
        raise ValidationError("El tamaño real del archivo no coincide con lo declarado.")

    reservation.status = QuotaReservation.Status.CONFIRMED
    reservation.save(update_fields=["status"])

    file.status = File.Status.AVAILABLE
    file.save(update_fields=["status", "updated_at"])

    return file


def request_download(*, file, owner):
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")  # RN-E3-06/RN-E3-40
    if file.status not in [File.Status.AVAILABLE, File.Status.TRASHED]:
        raise ValidationError("Este archivo no está disponible para descarga.")

    return storage.generate_download_url(
        storage_key=file.storage_key, original_name=file.original_name
    )