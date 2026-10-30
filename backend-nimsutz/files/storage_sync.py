# files/storage_sync.py
"""
Sincronización entre PostgreSQL y el almacenamiento (MinIO, R2, S3...).

No comparten transacción, así que se sigue siempre la misma regla: la base de datos
manda y el almacenamiento se limpia después. Primero se confirma el cambio en PostgreSQL
(cuota liberada, archivo marcado como eliminado) y luego se intenta borrar el objeto.
Si ese borrado falla, el archivo queda con storage_purged_at vacío y la limpieza
periódica lo reintenta. El peor caso es un objeto huérfano invisible para el usuario,
nunca un archivo visible sin objeto.

Este módulo solo conoce la interfaz StorageBackend (storage.get_backend()), nunca boto3,
así que sirve igual para MinIO, R2 o S3.

Lo usan services.py (confirmar subidas y eliminar definitivamente) y el comando
cleanup_expired_uploads, que debe correr cada minuto.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import storage
from .models import File, QuotaReservation
from .quota import lock_owner
from .storage.base import StorageError

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_PURGE_FAILURES = 3


# --- Puntos de entrada del comando cleanup_expired_uploads -------------------------

def release_expired_reservations(batch_size=200):
    """
    Libera las reservas pendientes cuyo plazo venció: subidas que nunca se completaron
    o nunca se confirmaron. Devuelve cuántas liberó.
    La base de datos se actualiza primero; el borrado del objeto va después y, si falla,
    queda pendiente para purge_pending_objects.
    """
    candidates = list(
        QuotaReservation.objects.filter(
            status=QuotaReservation.Status.PENDING, expires_at__lte=timezone.now()
        )
        .order_by("expires_at")
        .values_list("pk", "owner_id")[:batch_size]
    )

    released = 0
    discarded = []
    for reservation_id, owner_id in candidates:
        with transaction.atomic():
            lock_owner(owner_id)
            # Se vuelve a leer bajo el candado: otra petición pudo confirmarla mientras tanto.
            reservation = (
                QuotaReservation.objects.select_related("file")
                .filter(
                    pk=reservation_id,
                    status=QuotaReservation.Status.PENDING,
                    expires_at__lte=timezone.now(),
                )
                .first()
            )
            if reservation is None:
                continue

            reservation.status = QuotaReservation.Status.RELEASED
            reservation.save(update_fields=["status"])

            file = reservation.file
            if file is not None and file.status == File.Status.UPLOADING:
                file.status = File.Status.DELETED
                file.save(update_fields=["status", "updated_at"])
                discarded.append(file)
            released += 1

    # Fuera de las transacciones: la red no debe retener bloqueos de la base de datos.
    _purge_batch(discarded)
    return released


def purge_pending_objects(batch_size=200):
    """Reintenta el borrado de objetos de archivos ya eliminados. Devuelve (limpiados, pendientes)."""
    pending = list(
        File.objects.filter(status=File.Status.DELETED, storage_purged_at__isnull=True)
        .order_by("updated_at")[:batch_size]
    )
    purged = _purge_batch(pending)
    return purged, len(pending) - purged


# --- Piezas que también usa services.py ---------------------------------------------

def purge_file_object(file):
    """
    Borra del almacenamiento el objeto de un archivo que ya está eliminado en la base de datos.
    Devuelve True si quedó limpio. Es idempotente: borrar algo que no existe no falla.
    Si falla, storage_purged_at queda vacío y la limpieza periódica lo reintenta.

    Se usa en: services.confirm_upload (objeto inválido) y services.permanently_delete_file.
    """
    try:
        storage.get_backend().delete_object(storage_key=file.storage_key)
    except StorageError:
        logger.warning("No se pudo borrar el objeto del archivo %s; se reintentará.", file.pk)
        return False
    File.objects.filter(pk=file.pk).update(storage_purged_at=timezone.now())
    return True


def object_problem(file, metadata):
    """
    Motivo por el que el objeto subido no corresponde a lo reservado, o None si es válido.
    No se confía en lo que declaró el cliente: se compara con el objeto real.

    Se usa en: services.confirm_upload.
    """
    size = metadata.get("ContentLength")
    if size != file.size_bytes:
        return "El tamaño real del archivo no coincide con lo declarado."  # RN-T-08
    if size > settings.MAX_FILE_SIZE_BYTES:
        return "El archivo excede el límite permitido."
    stored_type = (metadata.get("ContentType") or "").split(";")[0].strip().lower()
    if stored_type != file.content_type.lower():
        return "El tipo del archivo no coincide con lo declarado."
    return None


# --- Interno ------------------------------------------------------------------------

def _purge_batch(files):
    """
    Borra objetos en orden. Se detiene tras varios fallos seguidos: lo más probable es que el
    almacenamiento esté caído y seguir solo haría esperar timeouts. Devuelve cuántos quedaron limpios.
    """
    purged = failures = 0
    for file in files:
        if purge_file_object(file):
            purged += 1
            failures = 0
        else:
            failures += 1
            if failures >= MAX_CONSECUTIVE_PURGE_FAILURES:
                break
    return purged