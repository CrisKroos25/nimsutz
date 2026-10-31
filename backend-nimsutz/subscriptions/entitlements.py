"""Aplicación de derechos, llamada únicamente tras verificar un pago aprobado."""

from .calendar import calculate_cycle_interval, to_guatemala
from .coverage import project_period, select_pending
from .history import record_period, replace_from
from .models import CoveragePeriod, ScheduledChange


def activate_contract(user, current, version, conditions, payment, at):
    sub = current or select_pending(user, version, at)
    # Cierra Gratis conservando el intervalo original como sustituido.
    for old in sub.coverage_history.filter(
        state=CoveragePeriod.State.VALID, ends_at__isnull=True
    ):
        old.state = CoveragePeriod.State.SUPERSEDED
        old.save(update_fields=["state"])
        record_period(
            sub,
            old.plan_version,
            old.starts_at,
            at,
            reason="retained",
            conditions=old.conditions,
            cycle_start=old.cycle_starts_at,
            supersedes=old,
        )
    start, end = calculate_cycle_interval(at)
    sub.cycle_anchor_day = to_guatemala(at).day
    period = record_period(
        sub,
        version,
        start,
        end,
        reason="contract",
        conditions=conditions,
        payment=payment,
    )
    ScheduledChange.objects.filter(user=user).delete()
    return project_period(sub, period, at)


def renew_contract(user, current, version, conditions, payment, at):
    start = current.expires_at
    _, end = calculate_cycle_interval(start, current.cycle_anchor_day)
    record_period(
        current,
        version,
        start,
        end,
        reason="renew",
        conditions=conditions,
        payment=payment,
    )
    ScheduledChange.objects.filter(user=user).update(effective_at=end)
    return project_period(current, current._effective_period, at)


def upgrade_contract(user, current, version, conditions, payment, at):
    replace_from(
        current, version, at, reason="upgrade", conditions=conditions, payment=payment
    )
    from .history import period_at

    return project_period(current, period_at(current, at), at)
