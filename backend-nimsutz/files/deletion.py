"""Borrado durable de objetos de una cuenta, sin conservar perfiles ni archivos."""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, Max
from django.db.models.functions import Cast
from django.utils import timezone

from . import storage
from .models import File, Folder, PendingObjectDeletion, QuotaReservation
from .storage.base import StorageError

logger = logging.getLogger(__name__)
MAX_CONSECUTIVE_FAILURES = 3


def queue_owner_objects(owner):
    """Se ejecuta en la misma transacción que borra al propietario."""
    now = timezone.now()
    ttl = timedelta(minutes=settings.RESERVATION_TTL_MINUTES)
    files = File.objects.filter(owner=owner).annotate(
        last_grant=Max("reservations__expires_at")
    )
    tasks = [
        PendingObjectDeletion(
            storage_key=file.storage_key,
            finalize_after=max(now, file.created_at + ttl, file.last_grant or now),
        )
        for file in files
    ]
    for model in (File, Folder, QuotaReservation):
        owned_ids = (
            model.objects.filter(owner=owner)
            .annotate(object_id=Cast("pk", output_field=CharField()))
            .values("object_id")
        )
        LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(model),
            object_id__in=owned_ids,
        ).delete()
    return [
        task.pk
        for task in PendingObjectDeletion.objects.bulk_create(tasks, batch_size=500)
    ]


def purge_account_objects(*, task_ids=None, batch_size=200):
    tasks = PendingObjectDeletion.objects.order_by("finalize_after", "pk")
    if task_ids is not None:
        tasks = tasks.filter(pk__in=task_ids)
    tasks = tasks[:batch_size]
    completed = 0
    failures = 0
    for task in tasks:
        try:
            storage.get_backend().delete_object(storage_key=task.storage_key)
        except StorageError:
            logger.warning(
                "Borrado de objeto pendiente de reintento: tarea %s.", task.pk
            )
            failures += 1
            if failures >= MAX_CONSECUTIVE_FAILURES:
                break  # Un almacenamiento caído no debe acumular cientos de timeouts.
            continue
        failures = 0
        # Una URL de carga ya emitida puede volver a crear el objeto. Se vuelve a
        # borrar después de vencerla, aunque la primera eliminación haya funcionado.
        if task.finalize_after <= timezone.now():
            completed += PendingObjectDeletion.objects.filter(pk=task.pk).delete()[0]
    return completed
