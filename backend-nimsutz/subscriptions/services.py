# subscriptions/services.py  (reemplaza el archivo completo)
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .errors import SubscriptionError
from .models import Plan, PlanVersion, Subscription, SubscriptionPreference

logger = logging.getLogger(__name__)

FREE_PLAN_CODE = "free"


def _latest_version(plan):
    # Usa .all() para aprovechar un prefetch si lo hay.
    return max(plan.versions.all(), key=lambda v: v.version_number, default=None)


def get_current_version(plan_code):
    plan = Plan.objects.filter(code=plan_code, is_available=True).first()
    if plan is None:
        raise SubscriptionError("plan_unavailable", "El plan no está disponible.")  # RN-E2-05
    version = _latest_version(plan)
    if version is None:
        raise SubscriptionError(
            "plan_without_version",
            "El plan no tiene condiciones definidas y no puede contratarse.",
        )
    return version


def is_contractable(version):
    # Los planes pagados no se contratan hasta que exista el flujo de pago.
    return version.plan.is_available and (version.price == 0 or settings.PAID_PLANS_ENABLED)


def version_payload(version):
    return {
        "plan_code": version.plan.code,
        "name": version.plan.name,
        "description": version.plan.description,
        "version_id": version.pk,
        "price": str(version.price),
        "currency": version.currency,
        "duration_days": version.duration_days,
        "capacity_bytes": version.capacity_bytes,
        "requires_payment": version.price > 0,
        "contractable": is_contractable(version),
    }


def list_catalog():
    items = []
    plans = Plan.objects.filter(is_available=True).prefetch_related("versions").order_by("id")
    for plan in plans:
        version = _latest_version(plan)
        if version is None:
            logger.warning("Plan '%s' está disponible pero no tiene versiones.", plan.code)
            continue  # situación inválida: un plan sin condiciones no se publica
        version.plan = plan
        items.append(version_payload(version))
    return items


def get_active_subscription(user):
    """Cobertura efectiva. Marca como vencida la que ya pasó su fecha (RN-E2-15/16)."""
    sub = (
        Subscription.objects.select_related("plan_version__plan")
        .filter(user=user, status=Subscription.Status.ACTIVE)
        .first()
    )
    if sub and sub.expires_at is not None and sub.expires_at <= timezone.now():
        sub.status = Subscription.Status.EXPIRED
        sub.save(update_fields=["status"])
        return None
    return sub


def subscription_payload(sub):
    return {
        "id": sub.pk,
        "status": sub.status,
        "started_at": sub.started_at,
        "expires_at": sub.expires_at,
        "plan": {
            "plan_code": sub.plan_version.plan.code,
            "version_id": sub.plan_version_id,
            "name": sub.plan_version.plan.name,
            "capacity_bytes": sub.plan_version.capacity_bytes,
        },
    }


@transaction.atomic
def activate_free(*, user):
    if not user.can_use_private_features:
        raise SubscriptionError(
            "account_not_eligible", "La cuenta debe estar verificada y activa para elegir un plan."
        )

    get_user_model().objects.select_for_update().get(pk=user.pk)  # serializa activaciones

    current = get_active_subscription(user)
    if current is not None:
        if current.plan_version.plan.code == FREE_PLAN_CODE:
            return current, False  # idempotente
        raise SubscriptionError("coverage_conflict", "Ya tienes una cobertura activa distinta a Gratis.")

    version = get_current_version(FREE_PLAN_CODE)
    subscription = Subscription.objects.create(
        user=user, plan_version=version, started_at=timezone.now(), expires_at=None
    )
    return subscription, True


def set_preference(*, user, plan_version_id):
    version = PlanVersion.objects.select_related("plan").filter(pk=plan_version_id).first()
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
    return preference  # no crea ni modifica cobertura


def get_preference(user):
    pref = SubscriptionPreference.objects.select_related("plan_version__plan").filter(user=user).first()
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