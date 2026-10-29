"""Único punto de integración con el contrato comercial de subscriptions."""
from collections.abc import Mapping

from subscriptions import services
from .errors import PaymentError


def _service(name):
    function = getattr(services, name, None)
    if not callable(function):
        raise PaymentError("payment_service_unavailable", "La contratación pagada todavía no está disponible.", 503)
    return function


def validate_quote(*, user, quote_id):
    quote = _service("validate_quote_for_execution")(user=user, quote_id=quote_id)
    if not isinstance(quote, Mapping):
        raise PaymentError("payment_service_unavailable", "No se pudo validar el resumen comercial.", 503)
    return quote


def apply_quote(*, user, quote, payment, approved_at):
    return _service("apply_approved_quote")(user=user, quote=quote, payment=payment, approved_at=approved_at)
