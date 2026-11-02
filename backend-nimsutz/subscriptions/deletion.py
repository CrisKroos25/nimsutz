"""Elimina exclusivamente la información comercial de una cuenta confirmada."""

from .models import CoveragePeriod, ScheduledOperation


def erase_customer_history(user):
    ScheduledOperation.objects.filter(owner=user).delete()
    periods = CoveragePeriod.objects.filter(subscription__user=user)
    # Primero retirar referencias internas protegidas; nunca tocar otra cuenta.
    periods.update(supersedes=None)
    periods.delete()
    # Suscripción, cotizaciones, preferencias y cambios se borran en cascada
    # cuando accounts elimina al usuario dentro de la misma transacción.
