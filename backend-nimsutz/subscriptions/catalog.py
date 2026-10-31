"""Catálogo público; no concede derechos de almacenamiento."""

import logging
from django.conf import settings
from .errors import SubscriptionError
from .models import Plan

logger = logging.getLogger(__name__)


def _latest_version(plan):
    # Usa .all() para aprovechar un prefetch si lo hay.
    return max(plan.versions.all(), key=lambda v: v.version_number, default=None)


def get_current_version(plan_code):
    plan = Plan.objects.filter(code=plan_code, is_available=True).first()
    if plan is None:
        raise SubscriptionError(
            "plan_unavailable", "El plan no está disponible."
        )  # RN-E2-05
    version = _latest_version(plan)
    if version is None:
        raise SubscriptionError(
            "plan_without_version",
            "El plan no tiene condiciones definidas y no puede contratarse.",
        )
    return version


def is_contractable(version):
    # Los planes pagados se pueden cotizar y contratar si el plan está disponible
    return version.plan.is_available and (
        version.price == 0 or getattr(settings, "PAID_PLANS_ENABLED", True)
    )


def version_payload(version):
    return {
        "plan_code": version.plan.code,
        "name": version.name,
        "description": version.plan.description,
        "version_id": version.pk,
        "price": str(version.price),
        "currency": version.currency,
        "duration_days": version.duration_days,
        "periodicity": "calendar_month" if version.price > 0 else None,
        "capacity_bytes": version.capacity_bytes,
        "requires_payment": version.price > 0,
        "contractable": is_contractable(version),
    }


def list_catalog():
    items = []
    plans = (
        Plan.objects.filter(is_available=True)
        .prefetch_related("versions")
        .order_by("id")
    )
    for plan in plans:
        version = _latest_version(plan)
        if version is None:
            logger.warning(
                "Plan '%s' está disponible pero no tiene versiones.", plan.code
            )
            continue  # situación inválida: un plan sin condiciones no se publica
        version.plan = plan
        items.append(version_payload(version))
    return items
