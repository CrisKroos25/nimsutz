# subscriptions/exception_handler.py
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .errors import SubscriptionError


def api_exception_handler(exc, context):
    """Único punto donde un SubscriptionError se vuelve respuesta HTTP.
    Todo lo demás lo sigue manejando DRF igual que antes."""
    if isinstance(exc, SubscriptionError):
        return Response(exc.as_body(), status=exc.http_status)
    return drf_exception_handler(exc, context)