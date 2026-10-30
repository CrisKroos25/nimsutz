# files/services.py
import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from . import storage
from .models import File, Folder, QuotaReservation
from .quota import get_available_quota, get_capacity_bytes, get_coverage, get_used_bytes, lock_owner  # noqa: F401
from .storage.base import StorageError
from .storage_sync import object_problem, purge_file_object

logger = logging.getLogger(__name__)


class StorageUnavailableError(Exception):
    """El almacenamiento no respondió. El estado en la base de datos no se modificó."""


# Subida de archivos

def request_upload(*, owner, folder, original_name, content_type, size_bytes):
    """
    Paso 1 de la subida: valida, reserva cuota y entrega la URL prefirmada.
    El archivo queda UPLOADING con una reserva PENDING que vence sola si nunca se confirma.
    """
    normalized_name = original_name.strip()
    storage_key = File.generate_storage_key(owner.id, normalized_name)

    try:
        with transaction.atomic():
            # lock_owner (quota.py): peticiones simultáneas del mismo usuario se ejecutan una detrás de otra, así dos subidas no pueden reservar la misma cuota libre.
            lock_owner(owner.pk)

            if get_coverage(owner) is None:
                raise ValidationError("Necesitas un plan activo para subir archivos.")  # sin plan = sin almacenamiento

            if folder is not None and folder.owner_id != owner.id:
                raise ValidationError("La carpeta no pertenece al usuario.")  # RN-E3-04/05

            if content_type not in settings.ALLOWED_CONTENT_TYPES:
                raise ValidationError("Tipo de archivo no permitido.")  # RN-E3-18

            if size_bytes <= 0 or size_bytes > settings.MAX_FILE_SIZE_BYTES:
                raise ValidationError("El tamaño del archivo excede el límite permitido.")  # RN-E3-17

            name_taken = File.objects.filter(
                owner=owner,
                folder=folder,
                original_name__iexact=normalized_name,
                status__in=[File.Status.UPLOADING, File.Status.AVAILABLE],
            ).exists()
            if name_taken:
                raise ValidationError("Ya existe un archivo con ese nombre en esta carpeta.")  # RN-E3-15/16

            # get_available_quota (quota.py): capacidad del plan - consumo (incluye papelera y reservas pendientes vigentes).
            if get_available_quota(owner) < size_bytes:
                raise ValidationError("Cuota insuficiente para este archivo.")  # RN-E3-25

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
    except IntegrityError:
        raise ValidationError("Ya existe un archivo con ese nombre en esta carpeta.")

    # La firma se calcula localmente; no toca la base de datos ni la red.
    upload_url = storage.get_backend().generate_upload_url(
        storage_key=storage_key,
        content_type=content_type,
        expires_in=settings.RESERVATION_TTL_MINUTES * 60,
    )

    return file, upload_url


def confirm_upload(*, file, owner):
    """
    Paso 2 de la subida: comprueba que el objeto real coincide con lo reservado y recién
    entonces marca el archivo como disponible. Un objeto inválido nunca queda disponible.
    """
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")  # RN-E3-06

    if file.status == File.Status.AVAILABLE:
        return file  # idempotente: la confirmación ya se había hecho
    if file.status != File.Status.UPLOADING:
        raise ValidationError("Este archivo ya fue confirmado o ya no está pendiente.")

    # 1) Se consulta el almacenamiento ANTES del candado: la red no debe retener la base de datos.
    try:
        metadata = storage.get_backend().head_object(storage_key=file.storage_key)
    except StorageError as exc:
        logger.warning("El almacenamiento no respondió al verificar el archivo %s.", file.pk)
        raise StorageUnavailableError(
            "El almacenamiento no está disponible. Inténtalo de nuevo."
        ) from exc

    problem = None
    with transaction.atomic():
        lock_owner(owner.pk)

        # 2) Con el candado puesto se vuelve a leer todo: la limpieza u otra confirmación pudo adelantarse mientras se consultaba el almacenamiento.
        current = File.objects.get(pk=file.pk)
        if current.status == File.Status.AVAILABLE:
            return current
        if current.status != File.Status.UPLOADING:
            raise ValidationError("Este archivo ya fue confirmado o ya no está pendiente.")

        reservation = QuotaReservation.objects.filter(
            file=current, status=QuotaReservation.Status.PENDING
        ).first()
        if reservation is None:
            raise ValidationError("No hay una reserva pendiente para este archivo.")

        if reservation.expires_at <= timezone.now():
            problem = "La reserva de espacio venció. Vuelve a subir el archivo."
        elif metadata is None:
            problem = "El archivo no fue subido a almacenamiento."  # RN-E3-38
        else:
            # object_problem (storage_sync.py): compara tamaño y tipo reales con lo reservado.
            problem = object_problem(current, metadata)

        if problem is None:
            reservation.status = QuotaReservation.Status.CONFIRMED
            reservation.save(update_fields=["status"])
            current.status = File.Status.AVAILABLE
            current.save(update_fields=["status", "updated_at"])
        else:
            # Se libera la cuota y el archivo se descarta.
            reservation.status = QuotaReservation.Status.RELEASED
            reservation.save(update_fields=["status"])
            current.status = File.Status.DELETED
            current.save(update_fields=["status", "updated_at"])

    # 3) Ya fuera de la transacción: el descarte quedó guardado. Se borra el objeto del almacenamiento (si existe) y se reintenta periódicamente si falla.
    if problem is not None:
        purge_file_object(current)
        raise ValidationError(problem)

    return current


# Descarga

def request_download(*, file, owner):
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")  # RN-E3-06/RN-E3-40
    if file.status not in [File.Status.AVAILABLE, File.Status.TRASHED]:
        raise ValidationError("Este archivo no está disponible para descarga.")

    return storage.get_backend().generate_download_url(
        storage_key=file.storage_key, original_name=file.original_name
    )


# Papelera y eliminación

def trash_file(*, file, owner):
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")  # RN-E3-06

    if file.status == File.Status.TRASHED:
        return file  # idempotente: ya está en papelera, sin efecto

    if file.status != File.Status.AVAILABLE:
        raise ValidationError("Solo un archivo disponible puede enviarse a papelera.")

    file.status = File.Status.TRASHED
    file.trashed_at = timezone.now()
    file.save(update_fields=["status", "trashed_at", "updated_at"])
    # RN-E3-28: eliminación lógica, el almacenamiento no se toca.
    # RN-E3-24: la reserva de cuota sigue en CONFIRMED, sigue consumiendo espacio.
    return file


def restore_file(*, file, owner, new_name=None):
    """
    Saca un archivo de la papelera. La papelera ya cuenta en la cuota, así que restaurar
    no consume espacio nuevo; solo se bloquea si el usuario está en exceso de cuota
    (plan reducido o vencido). Consultar, descargar y eliminar siguen permitidos.
    """
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")

    try:
        with transaction.atomic():
            # Mismo candado que el resto de operaciones de cuota, y se relee el archivo
            # bajo bloqueo: otra petición pudo restaurarlo o eliminarlo mientras tanto.
            lock_owner(owner.pk)
            current = File.objects.select_for_update().get(pk=file.pk)

            if current.status != File.Status.TRASHED:
                raise ValidationError("Solo un archivo en papelera puede restaurarse.")

            target_name = (new_name or current.original_name).strip()

            conflict = (
                File.objects.filter(
                    owner=owner,
                    folder=current.folder,
                    original_name__iexact=target_name,
                    status__in=[File.Status.UPLOADING, File.Status.AVAILABLE],
                )
                .exclude(pk=current.pk)
                .exists()
            )
            if conflict:
                raise ValidationError(
                    "Ya existe un archivo con ese nombre en esta carpeta. "
                    "Proporciona un nuevo nombre para restaurar."
                )  # RN-E3-32

            if get_available_quota(owner) < 0:
                raise ValidationError("No hay cuota suficiente para restaurar este archivo.")  # RN-E3-31

            current.status = File.Status.AVAILABLE
            current.original_name = target_name
            current.trashed_at = None
            current.save(update_fields=["status", "original_name", "trashed_at", "updated_at"])
    except IntegrityError:
        # La restricción única de la base de datos respalda la comprobación de nombre.
        raise ValidationError(
            "Ya existe un archivo con ese nombre en esta carpeta. "
            "Proporciona un nuevo nombre para restaurar."
        )

    return current


def permanently_delete_file(*, file, owner):
    if file.owner_id != owner.id:
        raise ValidationError("El archivo no pertenece al usuario.")

    # 1) Primero la base de datos: el archivo deja de existir para el usuario y la cuota se libera.
    with transaction.atomic():
        lock_owner(owner.pk)
        current = File.objects.select_for_update().get(pk=file.pk)

        if current.status != File.Status.TRASHED:
            raise ValidationError("Solo un archivo en papelera puede eliminarse definitivamente.")
            # RN-E3-33: la confirmación del usuario es responsabilidad del frontend

        QuotaReservation.objects.filter(
            file=current, status=QuotaReservation.Status.CONFIRMED
        ).update(status=QuotaReservation.Status.RELEASED)  # RN-E3-34

        current.status = File.Status.DELETED
        current.save(update_fields=["status", "updated_at"])

    # 2) Después el almacenamiento (RN-E3-35). purge_file_object (storage_sync.py): si falla,
    #    el usuario ya no ve el archivo y la limpieza periódica reintenta el borrado.
    purge_file_object(current)
    return current


# Carpetas

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