import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from subscriptions import services as subscriptions

from . import commercial
from .errors import PaymentError
from .models import CardMovement, Payment, PaymentDetail, TestCard


GUATEMALA = ZoneInfo("America/Guatemala")


def require_customer(user):
    if not user.is_active or not user.can_use_private_features or user.role != "cliente":
        raise PaymentError("account_not_eligible", "Necesitas una cuenta cliente activa y verificada.", 403)


def _digest(quote_id, card_data):
    key = getattr(settings, "PAYMENTS_IDEMPOTENCY_SECRET", "")
    if len(key) < 32:
        raise PaymentError("payment_service_unavailable", "El servicio de pagos requiere configuración.", 503)
    payload = json.dumps({"quote_id": str(quote_id), "card": card_data}, sort_keys=True, separators=(",", ":"))
    return hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _validated_terms(quote, quote_id):
    try:
        amount = Decimal(quote["total"])
        expires = parse_datetime(quote["expires_at"])
        lines = quote["lines"]
        line_total = sum((Decimal(line["amount"]) for line in lines), Decimal("0"))
        valid = (UUID(str(quote["id"])) == quote_id and quote["requires_payment"] is True
                 and quote["operation"] in {"contract", "renew", "change"}
                 and quote["currency"] == "GTQ" and amount.is_finite()
                 and 0 <= amount <= Decimal("9999999999.99") and amount == amount.quantize(Decimal("0.01"))
                 and bool(lines) and amount == line_total and isinstance(quote["plan"], dict)
                 and expires is not None and timezone.is_aware(expires))
        for line in lines:
            value = Decimal(line["amount"])
            valid = valid and value.is_finite() and value >= 0 and value == value.quantize(Decimal("0.01"))
            valid = valid and 0 < len(line["code"]) <= 40 and 0 < len(line["description"]) <= 255
    except (KeyError, TypeError, ValueError, InvalidOperation):
        valid = False
    if not valid:
        raise PaymentError("payment_service_unavailable", "El resumen comercial no es válido.", 503)
    if expires <= timezone.now():
        raise PaymentError("quote_expired", "El resumen venció. Revisa las condiciones nuevamente.")
    return amount


def _card_rejection(card, data, amount, currency):
    if card is None:
        return "card_not_found"
    if (card.holder != data["holder"] or card.expiry_month != data["expiry_month"]
            or card.expiry_year != data["expiry_year"]
            or not check_password(data["security_code"], card.security_code_hash)):
        return "card_details_invalid"
    if not card.enabled:
        return "card_disabled"
    now = timezone.localtime(timezone.now(), GUATEMALA)
    if (card.expiry_year, card.expiry_month) < (now.year, now.month):
        return "card_expired"
    if card.currency != currency:
        return "currency_mismatch"
    if card.balance < amount:
        return "insufficient_funds"
    return None


def payment_payload(payment):
    return {"id": payment.pk, "reference": str(payment.reference), "status": payment.status,
            "reason_code": payment.reason_code, "operation": payment.operation,
            "amount": str(payment.amount), "currency": payment.currency,
            "created_at": payment.created_at.isoformat(), "card_last4": payment.card_last4}


def _result(payment, replayed):
    return {**payment.result_snapshot, "payment": payment_payload(payment), "replayed": replayed}


@transaction.atomic
def execute_checkout(*, user, quote_id, operation_key, card_data):
    # El bloqueo del propietario serializa intentos con claves iguales o diferentes.
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    require_customer(user)
    digest = _digest(quote_id, card_data)
    previous = Payment.objects.filter(owner=user, operation_key=operation_key).first()
    if previous:
        if not hmac.compare_digest(previous.request_digest, digest):
            raise PaymentError("idempotency_conflict", "Esta clave ya corresponde a otra solicitud.")
        return _result(previous, True)
    if Payment.objects.filter(owner=user, quote_id=quote_id, status=Payment.Status.APPROVED).exists():
        raise PaymentError("quote_already_processed", "Esta cotización ya fue pagada.")
    quote = commercial.validate_quote(user=user, quote_id=quote_id)
    amount = _validated_terms(quote, quote_id)
    card = TestCard.objects.select_for_update().filter(number=card_data["number"]).first()
    reason = _card_rejection(card, card_data, amount, quote["currency"])
    payment = Payment.objects.create(
        owner=user, operation_key=operation_key, request_digest=digest, quote_id=quote_id,
        status=Payment.Status.REJECTED if reason else Payment.Status.APPROVED,
        reason_code=reason, operation=quote["operation"], amount=amount, currency=quote["currency"],
        card_last4=card.number[-4:] if card else "", plan_snapshot=quote["plan"],
    )
    PaymentDetail.objects.bulk_create([PaymentDetail(payment=payment, code=line["code"],
        description=line["description"], amount=Decimal(line["amount"])) for line in quote["lines"]])
    if reason is None:
        card.balance -= amount
        card.save(update_fields=["balance"])
        CardMovement.objects.create(card=card, payment=payment, amount=amount, balance_after=card.balance)
        subscription = commercial.apply_quote(user=user, quote=quote, payment=payment, approved_at=timezone.now())
        if subscription is None:
            raise PaymentError("payment_service_unavailable", "No se pudo aplicar la cobertura.", 503)
    else:
        subscription = subscriptions.get_active_subscription(user)
    snapshot = {"subscription": subscriptions.subscription_payload(subscription) if subscription else None,
                "destination": subscriptions.resolve_destination(user)}
    payment.result_snapshot = json.loads(json.dumps(snapshot, cls=DjangoJSONEncoder))
    payment.save(update_fields=["result_snapshot"])
    return _result(payment, False)


def get_operation_result(*, user, operation_key):
    require_customer(user)
    payment = Payment.objects.filter(owner=user, operation_key=operation_key).first()
    if payment is None:
        raise PaymentError("operation_not_found", "Todavía no hay un resultado para esta operación.", 404)
    return _result(payment, True)


def get_payment_result(*, user, payment_id):
    require_customer(user)
    payment = Payment.objects.filter(owner=user, pk=payment_id).first()
    if payment is None:
        raise PaymentError("not_found", "No se encontró el pago.", 404)
    return _result(payment, True)
