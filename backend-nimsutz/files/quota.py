# files/quota.py
"""
Cuota de almacenamiento: cuánto puede guardar un usuario y cuánto ha consumido.

Regla de oro: toda operación que CAMBIE la cuota (reservar, confirmar, restaurar,
eliminar definitivamente, liberar reservas vencidas) debe tomar primero lock_owner()
dentro de una transacción. Así dos peticiones simultáneas del mismo usuario nunca
leen la misma cuota libre a la vez.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.utils import timezone

from subscriptions.services import resolve_effective_subscription

from .models import QuotaReservation


def lock_owner(owner_id):
    """
    Candado por usuario: dos operaciones que cambian la cuota del mismo usuario
    se ejecutan una detrás de otra. Debe llamarse dentro de transaction.atomic().

    Se usa en: services.request_upload, confirm_upload, restore_file,
    permanently_delete_file y storage_sync.release_expired_reservations.
    """
    get_user_model().objects.select_for_update().get(pk=owner_id)


def get_coverage(owner):
    """
    Cobertura efectiva del usuario (su suscripción vigente), o None si no tiene.

    Usa resolve_effective_subscription, que además aplica las transiciones de vencimiento:
    siguiente ciclo pagado, cambio programado o regreso automático a Gratis (conservando
    archivos). Así la capacidad de un usuario no se queda en 0 solo porque su plan venció.
    """
    return resolve_effective_subscription(owner)


def get_available_quota(owner):
    """
    RN-E3-22/23/24: disponible = capacidad de la cobertura - consumo
    (archivos activos + reservas pendientes, incluye papelera).
    Un valor negativo significa exceso de cuota: se bloquean la carga y la restauración.

    Se usa en: services.request_upload y restore_file.
    """
    return get_capacity_bytes(owner) - get_used_bytes(owner)


def get_used_bytes(owner):
    """
    Consumo = archivos confirmados (la papelera incluida) + reservas pendientes VIGENTES.
    Una reserva pendiente vencida deja de contar aunque la limpieza aún no haya corrido.
    """
    counted = Q(status=QuotaReservation.Status.CONFIRMED) | Q(
        status=QuotaReservation.Status.PENDING, expires_at__gt=timezone.now()
    )
    return (
        QuotaReservation.objects.filter(owner=owner)
        .filter(counted)
        .aggregate(total=Sum("reserved_bytes"))["total"]
        or 0
    )


def get_capacity_bytes(owner):
    """Capacidad del plan de la cobertura efectiva. Sin cobertura no hay almacenamiento: 0."""
    coverage = get_coverage(owner)
    if coverage is None:
        return 0
    return coverage.plan_version.capacity_bytes