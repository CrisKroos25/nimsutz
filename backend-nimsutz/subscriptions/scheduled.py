"""Confirmación y cancelación de cambios sin cobro, con respuesta idempotente."""

from uuid import UUID
from .coverage import resolve_effective_subscription
from .errors import SubscriptionError
from .models import Quote, ScheduledChange, ScheduledOperation
from .payloads import scheduled_change_payload, subscription_payload
from .quotations import validate_locked_quote
from .terms import locked_customer, require_customer


def confirm_scheduled_quote(*, user, quote_id, operation_key=None):
    try:
        key = UUID(str(operation_key))
    except (ValueError, TypeError):
        raise SubscriptionError("invalid_request", "Se requiere Idempotency-Key UUID.")
    with locked_customer(user) as customer:
        require_customer(customer)
        previous = ScheduledOperation.objects.filter(
            owner=customer, operation_key=key
        ).first()
        if previous:
            if str(previous.quote_id) != str(quote_id):
                raise SubscriptionError(
                    "idempotency_conflict", "La clave ya corresponde a otra solicitud."
                )
            return previous.result
        quote = (
            Quote.objects.select_for_update(of=("self",))
            .select_related("plan_version__plan")
            .filter(pk=quote_id, user=customer)
            .first()
        )
        if quote is None:
            raise SubscriptionError("not_found", "Cotización no encontrada.")
        current = resolve_effective_subscription(customer)
        validate_locked_quote(customer, quote, current)
        if (
            current is None
            or quote.requires_payment
            or quote.effect.get("kind") not in {"schedule_free", "schedule_downgrade"}
        ):
            raise SubscriptionError(
                "invalid_request", "Esta cotización no es una programación sin cobro."
            )
        ScheduledChange.objects.update_or_create(
            user=customer,
            defaults={
                "subscription": current,
                "target_plan_version": quote.plan_version,
                "effective_at": current.coverage_end or current.expires_at,
                "requires_payment": quote.plan_version.price > 0,
            },
        )
        quote.status = Quote.Status.CONFIRMED
        quote.save(update_fields=["status"])
        result = {
            "scheduled_change": scheduled_change_payload(customer),
            "subscription": subscription_payload(current),
        }
        ScheduledOperation.objects.create(
            owner=customer, operation_key=key, quote=quote, result=result
        )
        return result


def cancel_scheduled_change(*, user):
    with locked_customer(user) as customer:
        require_customer(customer)
        ScheduledChange.objects.filter(user=customer).delete()
