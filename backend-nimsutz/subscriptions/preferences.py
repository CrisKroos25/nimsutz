"""Preferencias de navegación: no crean suscripción ni capacidad."""

from .catalog import _latest_version, get_current_version, version_payload
from .coverage import get_active_subscription
from .errors import SubscriptionError
from .models import PlanVersion, SubscriptionPreference


def set_preference(*, user, plan_version_id):
    version = (
        PlanVersion.objects.select_related("plan").filter(pk=plan_version_id).first()
    )
    if version is None or not version.plan.is_available:
        raise SubscriptionError(
            "plan_unavailable",
            "El plan seleccionado no está disponible.",
            {"plan_version_id": "Plan no disponible."},
        )
    if version.pk != get_current_version(version.plan.code).pk:
        raise SubscriptionError(
            "plan_conditions_changed",
            "Las condiciones del plan cambiaron. Vuelve a elegirlo.",
            {"plan_version_id": "Versión desactualizada."},
        )
    preference, _ = SubscriptionPreference.objects.update_or_create(
        user=user, defaults={"plan_version": version}
    )
    return preference


def get_preference(user):
    pref = (
        SubscriptionPreference.objects.select_related("plan_version__plan")
        .filter(user=user)
        .first()
    )
    if pref is None:
        return None
    version = pref.plan_version
    latest = _latest_version(version.plan) if version.plan.is_available else None
    payload = version_payload(version)
    payload["is_current"] = bool(latest and latest.pk == version.pk)
    payload["current_version_id"] = latest.pk if latest else None
    return payload


def resolve_destination(user):
    if user.role == user.Role.ADMINISTRADOR:
        return "admin"
    if get_active_subscription(user) is not None:
        return "files"
    if SubscriptionPreference.objects.filter(user=user).exists():
        return "plan_summary"
    return "plans"
