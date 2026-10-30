"""Registro de intervalos: se conservan originales al sustituirlos, sin borrar el pasado."""

from django.db.models import Q
from .models import CoveragePeriod, Subscription
from .terms import plan_conditions


def record_period(
    sub,
    version,
    start,
    end,
    *,
    reason,
    conditions=None,
    payment=None,
    cycle_start=None,
    cycle_end=None,
    supersedes=None
):
    if end is not None and start >= end:
        return None
    return CoveragePeriod.objects.create(
        subscription=sub,
        plan_version=version,
        conditions=conditions or plan_conditions(version),
        starts_at=start,
        ends_at=end,
        cycle_starts_at=cycle_start or start,
        cycle_ends_at=cycle_end if cycle_end is not None else end,
        reason=reason,
        payment=payment,
        supersedes=supersedes,
    )


def ensure_history(sub):
    # Compatibilidad con contratos previos y fixtures creados sin pasar por servicios.
    if (
        sub.status == Subscription.Status.PENDING
        or sub.coverage_history.exists()
        or sub.started_at is None
    ):
        return
    record_period(
        sub, sub.plan_version, sub.started_at, sub.expires_at, reason="legacy"
    )
    if (
        sub.next_cycle_starts_at
        and sub.next_cycle_ends_at
        and sub.next_cycle_plan_version_id
    ):
        record_period(
            sub,
            sub.next_cycle_plan_version,
            sub.next_cycle_starts_at,
            sub.next_cycle_ends_at,
            reason="legacy_renewal",
        )


def period_at(sub, at):
    return (
        sub.coverage_history.select_related("plan_version__plan")
        .filter(
            state=CoveragePeriod.State.VALID,
            starts_at__lte=at,
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at))
        .order_by("-starts_at", "-pk")
        .first()
    )


def replace_from(sub, version, at, *, reason, payment=None, conditions=None):
    originals = list(
        sub.coverage_history.filter(state=CoveragePeriod.State.VALID)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at))
        .order_by("starts_at")
    )
    for original in originals:
        original.state = CoveragePeriod.State.SUPERSEDED
        original.save(update_fields=["state"])
        if original.starts_at < at:
            record_period(
                sub,
                original.plan_version,
                original.starts_at,
                at,
                reason="retained",
                conditions=original.conditions,
                payment=original.payment,
                cycle_start=original.cycle_starts_at,
                cycle_end=original.cycle_ends_at,
                supersedes=original,
            )
        record_period(
            sub,
            version,
            max(at, original.starts_at),
            original.ends_at,
            reason=reason,
            conditions=conditions,
            payment=payment,
            cycle_start=original.cycle_starts_at,
            cycle_end=original.cycle_ends_at,
            supersedes=original,
        )
