"""Identidad, activación explícita y cobertura efectiva calculada desde el historial."""

from django.utils import timezone
from .calendar import to_guatemala
from .catalog import get_current_version
from .errors import SubscriptionError
from .history import ensure_history, period_at, record_period
from .models import CoveragePeriod, ScheduledChange, Subscription
from .terms import FREE_CODE, locked_customer, plan_conditions, require_customer


def select_pending(user, version, at):
    sub = Subscription.objects.filter(user=user).first()
    if sub is None:
        return Subscription.objects.create(
            user=user,
            status=Subscription.Status.PENDING,
            plan_version=version,
            started_at=None,
            selected_plan_version=version,
            selected_at=at,
            selected_conditions=plan_conditions(version),
        )
    if sub.status == Subscription.Status.PENDING and sub.plan_version_id != version.pk:
        sub.plan_version = version
        sub.selected_plan_version = version
        sub.selected_at = at
        sub.selected_conditions = plan_conditions(version)
        sub.save(
            update_fields=[
                "plan_version",
                "selected_plan_version",
                "selected_at",
                "selected_conditions",
            ]
        )
    return sub


def project_period(sub, period, at):
    future = (
        sub.coverage_history.filter(state=CoveragePeriod.State.VALID, starts_at__gt=at)
        .order_by("starts_at")
        .first()
    )
    sub.plan_version = period.plan_version
    sub.status = Subscription.Status.ACTIVE
    sub.started_at = period.cycle_starts_at
    sub.expires_at = (
        period.cycle_ends_at if period.conditions["plan_code"] != FREE_CODE else None
    )
    sub.coverage_end = future.ends_at if future else sub.expires_at
    sub.next_cycle_starts_at = future.starts_at if future else None
    sub.next_cycle_ends_at = future.ends_at if future else None
    sub.next_cycle_plan_version = future.plan_version if future else None
    sub.cycle_anchor_day = (
        (sub.cycle_anchor_day or to_guatemala(period.cycle_starts_at).day)
        if sub.expires_at
        else None
    )
    sub.save(
        update_fields=[
            "plan_version",
            "status",
            "started_at",
            "expires_at",
            "coverage_end",
            "next_cycle_starts_at",
            "next_cycle_ends_at",
            "next_cycle_plan_version",
            "cycle_anchor_day",
        ]
    )
    sub._effective_period = period
    return sub


def resolve_effective_subscription(user, at=None):
    reference = at or timezone.now()
    with locked_customer(user) as customer:
        sub = Subscription.objects.select_for_update().filter(user=customer).first()
        if sub is None or sub.status == Subscription.Status.PENDING:
            return None
        ensure_history(sub)
        period = period_at(sub, reference)
        if period is not None:
            return project_period(sub, period, reference)
        last = (
            sub.coverage_history.filter(
                state=CoveragePeriod.State.VALID, ends_at__lte=reference
            )
            .order_by("-ends_at")
            .first()
        )
        if last is None:
            return None  # Nunca conceder cobertura futura antes de su inicio.
        change = ScheduledChange.objects.filter(
            user=customer, effective_at__lte=reference
        ).first()
        # Una bajada pagada queda pendiente de pago. Nunca se concede por el reloj.
        if change and change.target_plan_version.price == 0:
            version = change.target_plan_version
            change.delete()
        else:
            version = get_current_version(FREE_CODE)
            if change and not change.requires_payment:
                change.requires_payment = True
                change.save(update_fields=["requires_payment"])
        record_period(sub, version, last.ends_at, None, reason="return_free")
        return project_period(sub, period_at(sub, reference), reference)


def get_active_subscription(user):
    return resolve_effective_subscription(user)


def activate_free(*, user, plan_version_id=None):
    with locked_customer(user) as customer:
        require_customer(customer)
        current = resolve_effective_subscription(customer)
        if current is not None:
            if current.plan_version.plan.code != FREE_CODE:
                raise SubscriptionError(
                    "coverage_conflict", "Ya tienes una cobertura pagada activa."
                )
            version = current.plan_version
            if plan_version_id is not None and version.pk != plan_version_id:
                raise SubscriptionError(
                    "plan_conditions_changed", "Revisa y confirma la versión de Gratis."
                )
            return current, False
        version = get_current_version(FREE_CODE)
        if version.price != 0 or (
            plan_version_id is not None and version.pk != plan_version_id
        ):
            raise SubscriptionError(
                "plan_conditions_changed", "Revisa y confirma la versión de Gratis."
            )
        at = timezone.now()
        sub = select_pending(customer, version, at)
        record_period(sub, version, at, None, reason="activate_free")
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["status"])
        ScheduledChange.objects.filter(user=customer).delete()
        return project_period(sub, period_at(sub, at), at), True
