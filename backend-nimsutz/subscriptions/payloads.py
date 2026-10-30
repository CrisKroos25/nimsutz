"""Proyección pública aditiva de suscripción, cotización y cambios programados."""

from .models import ScheduledChange, Subscription
from django.utils import timezone
from .terms import effective_conditions, iso


def subscription_payload(sub):
    if sub is None:
        return None
    conditions = effective_conditions(sub)
    return {
        "id": sub.pk,
        "status": sub.status,
        "started_at": iso(sub.started_at),
        "expires_at": iso(sub.expires_at),
        "cycle_anchor_day": sub.cycle_anchor_day,
        "coverage_end": iso(sub.coverage_end or sub.expires_at),
        "plan": {
            key: conditions[key]
            for key in ["plan_code", "version_id", "name", "capacity_bytes"]
        },
    }


def next_cycle_payload(sub):
    if sub is None or not sub.next_cycle_starts_at:
        return None
    return {
        "starts_at": iso(sub.next_cycle_starts_at),
        "ends_at": iso(sub.next_cycle_ends_at),
        "plan_version_id": sub.next_cycle_plan_version_id,
    }


def scheduled_change_payload(user):
    change = (
        ScheduledChange.objects.select_related("target_plan_version__plan")
        .filter(user=user)
        .first()
    )
    if change is None:
        return None
    return {
        "id": change.pk,
        "target_plan_code": change.target_plan_version.plan.code,
        "target_plan_version_id": change.target_plan_version_id,
        "effective_at": iso(change.effective_at),
        "requires_payment": change.requires_payment,
        "payment_due": change.requires_payment
        and change.effective_at <= timezone.now(),
    }


def pending_selection_payload(user):
    sub = Subscription.objects.filter(
        user=user, status=Subscription.Status.PENDING
    ).first()
    if sub is None:
        return None
    return {
        "subscription_id": sub.pk,
        "status": sub.status,
        "plan_version_id": sub.plan_version_id,
        "selected_at": iso(sub.selected_at),
        "plan": sub.selected_conditions,
    }


def get_allowed_actions(sub, user):
    if sub is None:
        return ["contract"]
    if sub.plan_version.plan.code == "free":
        return ["change"]
    return ["change"] + ([] if sub.next_cycle_starts_at else ["renew"])


def quote_payload(quote):
    return {
        "id": str(quote.pk),
        "operation": quote.operation,
        "expires_at": iso(quote.expires_at),
        "currency": quote.currency,
        "total": f"{quote.total:.2f}",
        "requires_payment": quote.requires_payment,
        "plan": quote.plan_snapshot,
        "lines": quote.lines,
        "effect": quote.effect,
    }
