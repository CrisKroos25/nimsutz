"""Cotizaciones del servidor: cada operación conserva su propio cálculo y validación."""

import uuid
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from .calendar import calculate_cycle_interval
from .catalog import get_current_version
from .coverage import resolve_effective_subscription, select_pending
from .entitlements import activate_contract, renew_contract, upgrade_contract
from .errors import SubscriptionError
from .models import Quote, ScheduledChange
from .payloads import quote_payload
from .proration import calculate_upgrade_proration, round_money
from .terms import (
    QUOTE_TTL_MINUTES,
    effective_conditions,
    execution_context,
    iso,
    locked_customer,
    plan_conditions,
    require_customer,
)


def target_version(version_id):
    from .models import PlanVersion

    version = PlanVersion.objects.select_related("plan").filter(pk=version_id).first()
    if version is None or not version.plan.is_available:
        raise SubscriptionError(
            "plan_unavailable", "El plan seleccionado no está disponible."
        )
    if get_current_version(version.plan.code).pk != version.pk:
        raise SubscriptionError(
            "plan_conditions_changed", "El catálogo cambió. Revisa sus condiciones."
        )
    return version


def require_capacity(user, version):
    from files.services import get_used_bytes

    if version.price > 0 and get_used_bytes(user) > version.capacity_bytes:
        raise SubscriptionError(
            "quota_exceeded", "El consumo actual supera la capacidad del plan destino."
        )


def create_quote(
    user,
    current,
    version,
    operation,
    lines,
    effect,
    at,
    *,
    requires_payment=True,
    conditions=None,
):
    conditions = conditions or plan_conditions(version)
    return Quote.objects.create(
        id=uuid.uuid4(),
        user=user,
        operation=operation,
        plan_version=version,
        currency=conditions["currency"],
        total=sum((Decimal(line["amount"]) for line in lines), Decimal("0.00")),
        requires_payment=requires_payment,
        lines=lines,
        effect=effect,
        plan_snapshot=conditions,
        execution_context=execution_context(user, current, conditions),
        expires_at=at + timedelta(minutes=QUOTE_TTL_MINUTES),
    )


def contract_quote(user, current, version_id, at):
    if current and current.plan_version.price > 0:
        raise SubscriptionError(
            "coverage_conflict", "Ya tienes una cobertura pagada activa."
        )
    version = target_version(version_id)
    if version.price <= 0:
        raise SubscriptionError(
            "invalid_request", "Confirma Gratis mediante activate-free."
        )
    require_capacity(user, version)
    select_pending(user, version, at)
    start, end = calculate_cycle_interval(at)
    return create_quote(
        user,
        current,
        version,
        "contract",
        [
            {
                "code": "contract_cycle",
                "description": f"Primer ciclo {version.name}",
                "amount": f"{version.price:.2f}",
            },
        ],
        {
            "kind": "activate",
            "starts_at": iso(start),
            "ends_at": iso(end),
            "scheduled_change_at": None,
        },
        at,
    )


def renewal_quote(user, current, version_id, at):
    if current is None or current.plan_version.price == 0:
        raise SubscriptionError(
            "coverage_conflict", "No tienes una suscripción pagada que renovar."
        )
    if current.next_cycle_starts_at:
        raise SubscriptionError(
            "renewal_limit_reached", "Ya tienes un siguiente ciclo anticipado pagado."
        )
    if version_id is not None and version_id != current.plan_version_id:
        raise SubscriptionError(
            "plan_conditions_changed", "La renovación conserva la versión contratada."
        )
    conditions = effective_conditions(current)
    start, end = calculate_cycle_interval(current.expires_at, current.cycle_anchor_day)
    return create_quote(
        user,
        current,
        current.plan_version,
        "renew",
        [
            {
                "code": "renewal_cycle",
                "description": f"Renovación ciclo {conditions['name']}",
                "amount": conditions["price"],
            },
        ],
        {
            "kind": "renew",
            "starts_at": iso(start),
            "ends_at": iso(end),
            "scheduled_change_at": (
                iso(end) if ScheduledChange.objects.filter(user=user).exists() else None
            ),
        },
        at,
        conditions=conditions,
    )


def upgrade_quote(user, current, version, at):
    conditions = effective_conditions(current)
    adjustment = calculate_upgrade_proration(
        now=at,
        cycle_start=current.started_at,
        cycle_end=current.expires_at,
        current_price=Decimal(conditions["price"]),
        target_price=version.price,
    )
    lines = [
        {
            "code": "current_cycle_adjustment",
            "description": f"Ajuste proporcional ciclo actual a {version.name}",
            "amount": f"{adjustment:.2f}",
        }
    ]
    if current.next_cycle_starts_at:
        difference = round_money(version.price - Decimal(conditions["price"]))
        lines.append(
            {
                "code": "next_cycle_adjustment",
                "description": f"Diferencia ciclo anticipado a {version.name}",
                "amount": f"{difference:.2f}",
            }
        )
    return create_quote(
        user,
        current,
        version,
        "change",
        lines,
        {
            "kind": "upgrade",
            "starts_at": iso(at),
            "ends_at": iso(current.expires_at),
            "scheduled_change_at": None,
        },
        at,
    )


def downgrade_quote(user, current, version, at):
    require_capacity(user, version)  # Gratis nunca se bloquea por exceso de consumo.
    end = current.coverage_end or current.expires_at
    return create_quote(
        user,
        current,
        version,
        "change",
        [
            {
                "code": "schedule_change",
                "description": f"Programar cambio a {version.name}",
                "amount": "0.00",
            },
        ],
        {
            "kind": "schedule_free" if version.price == 0 else "schedule_downgrade",
            "starts_at": iso(end),
            "ends_at": None,
            "scheduled_change_at": iso(end),
        },
        at,
        requires_payment=False,
    )


def change_quote(user, current, version_id, at):
    if current is None or current.plan_version.price == 0:
        return contract_quote(user, current, version_id, at)
    version = target_version(version_id)
    if version.plan_id == current.plan_version.plan_id:
        raise SubscriptionError("coverage_conflict", "Ya tienes contratado este plan.")
    require_capacity(user, version)
    if version.price > Decimal(effective_conditions(current)["price"]):
        return upgrade_quote(user, current, version, at)
    return downgrade_quote(user, current, version, at)


QUOTE_BUILDERS = {
    "contract": contract_quote,
    "renew": renewal_quote,
    "change": change_quote,
}


def prepare_quote(*, user, operation, plan_version_id=None):
    builder = QUOTE_BUILDERS.get(operation)
    if builder is None:
        raise SubscriptionError("invalid_request", "Operación comercial no admitida.")
    with locked_customer(user) as customer:
        require_customer(customer)
        current = resolve_effective_subscription(customer)
        return builder(customer, current, plan_version_id, timezone.now())


def get_quote(*, user, quote_id):
    require_customer(user)
    quote = (
        Quote.objects.select_related("plan_version__plan")
        .filter(pk=quote_id, user=user)
        .first()
    )
    if quote is None:
        raise SubscriptionError("not_found", "Cotización no encontrada.")
    if timezone.now() >= quote.expires_at:
        raise SubscriptionError(
            "quote_expired", "El resumen venció. Solicita uno nuevo."
        )
    return quote


def validate_locked_quote(user, quote, current):
    if quote.status != Quote.Status.PENDING:
        raise SubscriptionError(
            "quote_already_processed", "Esta cotización ya fue procesada."
        )
    if timezone.now() >= quote.expires_at:
        raise SubscriptionError(
            "quote_expired", "El resumen venció. Solicita uno nuevo."
        )
    if quote.operation == "renew":
        if current is None or current.plan_version.price == 0:
            raise SubscriptionError(
                "coverage_conflict", "No hay cobertura pagada para renovar."
            )
        if current.next_cycle_starts_at:
            raise SubscriptionError(
                "renewal_limit_reached", "Ya tienes un siguiente ciclo pagado."
            )
        conditions = effective_conditions(current)
    else:
        target_version(quote.plan_version_id)
        conditions = plan_conditions(quote.plan_version)
    if quote.execution_context != execution_context(user, current, conditions):
        raise SubscriptionError(
            "plan_conditions_changed",
            "La cobertura o las condiciones cambiaron. Revisa otro resumen.",
        )
    require_capacity(user, quote.plan_version)


def validate_quote_for_execution(*, user, quote_id):
    require_customer(user)
    quote = (
        Quote.objects.select_for_update(of=("self",))
        .select_related("plan_version__plan")
        .filter(pk=quote_id, user=user)
        .first()
    )
    if quote is None:
        raise SubscriptionError("not_found", "Cotización no encontrada.")
    current = resolve_effective_subscription(user)
    validate_locked_quote(user, quote, current)
    return quote_payload(quote)


ENTITLEMENT_HANDLERS = {
    "contract": activate_contract,
    "renew": renew_contract,
    "change": upgrade_contract,
}


def apply_approved_quote(*, user, quote, payment, approved_at=None):
    from payments.models import Payment

    if (
        payment is None
        or not Payment.objects.filter(
            pk=payment.pk,
            owner=user,
            quote_id=quote["id"],
            status="approved",
            amount=quote["total"],
            currency=quote["currency"],
        ).exists()
    ):
        raise SubscriptionError(
            "forbidden", "La cobertura requiere un pago aprobado de esta cotización."
        )
    with locked_customer(user) as customer:
        quote_obj = Quote.objects.select_for_update().get(pk=quote["id"], user=customer)
        current = resolve_effective_subscription(customer)
        validate_locked_quote(customer, quote_obj, current)
        if not quote_obj.requires_payment:
            raise SubscriptionError(
                "invalid_request",
                "La programación no concede cobertura mediante checkout.",
            )
        at = approved_at or timezone.now()
        sub = ENTITLEMENT_HANDLERS[quote_obj.operation](
            customer,
            current,
            quote_obj.plan_version,
            quote_obj.plan_snapshot,
            payment,
            at,
        )
        quote_obj.status = Quote.Status.EXECUTED
        quote_obj.save(update_fields=["status"])
        return sub
