"""Eliminación de la identidad y sus datos, coordinada por propietario."""

from django.db import transaction
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from files.deletion import purge_account_objects, queue_owner_objects
from files.models import PendingObjectDeletion
from payments.deletion import erase_customer_payments
from subscriptions.deletion import erase_customer_history

from .models import User
from .services import invalidate_user_sessions


def delete_own_account(user):
    with transaction.atomic():
        owner = User.objects.select_for_update().filter(pk=user.pk).first()
        if owner is None:
            return True  # Otra solicitud ya la eliminó; no afirmar que terminó el almacenamiento.
        tasks = queue_owner_objects(owner)
        erase_customer_history(owner)
        erase_customer_payments(owner)
        LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(User),
            object_id=str(owner.pk),
        ).delete()
        invalidate_user_sessions(owner, include_expired=True)
        owner.delete()
    # PostgreSQL ya confirmó el borrado y el trabajo de limpieza. La red no
    # retiene el bloqueo del usuario y un fallo de MinIO conserva el reintento.
    purge_account_objects(task_ids=tasks)
    return PendingObjectDeletion.objects.filter(pk__in=tasks).exists()
