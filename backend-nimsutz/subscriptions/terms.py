"""Condiciones históricas y comparaciones de una intención comercial."""

from contextlib import contextmanager
from django.contrib.auth import get_user_model
from django.db import transaction
from .calendar import to_guatemala
from .errors import SubscriptionError
from .models import ScheduledChange, Subscription

FREE_CODE = "free"
QUOTE_TTL_MINUTES = 15


def iso(value):
    return to_guatemala(value).isoformat() if value else None


def require_customer(user):
    if (
        not user.is_active
        or not user.can_use_private_features
        or user.role != "cliente"
    ):
        raise SubscriptionError(
            "account_not_eligible", "Necesitas una cuenta cliente activa y verificada."
        )


@contextmanager
def locked_customer(user):
    # Todos los caminos comerciales adquieren primero la misma identidad.
    with transaction.atomic():
        yield get_user_model().objects.select_for_update().get(pk=user.pk)


def plan_conditions(version):
    return {
        "plan_code": version.plan.code,
        "version_id": version.pk,
        "name": version.name or version.plan.name,
        "price": f"{version.price:.2f}",
        "currency": version.currency,
        "capacity_bytes": version.capacity_bytes,
        "duration_days": version.duration_days,
        "periodicity": None if version.price == 0 else "calendar_month",
    }


def effective_conditions(sub):
    period = getattr(sub, "_effective_period", None)
    return period.conditions if period else plan_conditions(sub.plan_version)


def execution_context(user, sub, target_conditions):
    selection = Subscription.objects.filter(
        user=user, status=Subscription.Status.PENDING
    ).first()
    change = ScheduledChange.objects.filter(user=user).first()
    return {
        "revision": 2,
        "subscription": (
            None
            if sub is None
            else {
                "id": sub.pk,
                "version_id": sub.plan_version_id,
                "started_at": iso(sub.started_at),
                "expires_at": iso(sub.expires_at),
                "coverage_end": iso(sub.coverage_end),
                "next_starts_at": iso(sub.next_cycle_starts_at),
                "next_ends_at": iso(sub.next_cycle_ends_at),
                "next_version_id": sub.next_cycle_plan_version_id,
            }
        ),
        "selection": (
            None
            if selection is None
            else {"id": selection.pk, "version_id": selection.plan_version_id}
        ),
        "target": target_conditions,
        "scheduled_change": (
            None
            if change is None
            else {
                "id": change.pk,
                "version_id": change.target_plan_version_id,
                "effective_at": iso(change.effective_at),
            }
        ),
    }
