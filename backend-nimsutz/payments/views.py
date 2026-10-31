from uuid import UUID

from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from subscriptions.errors import SubscriptionError

from . import services
from .errors import PaymentError
from .serializers import CheckoutInputSerializer


class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, PaymentError):
            return Response(exc.as_body(), status=exc.status)
        if isinstance(exc, SubscriptionError):
            return Response(exc.as_body(), status=exc.http_status)
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated, PermissionDenied)):
            code = "csrf_failed" if "csrf" in str(exc).lower() else "forbidden"
            return Response({"code": code, "detail": str(exc.detail), "field_errors": {}}, status=403)
        return super().handle_exception(exc)


@method_decorator(sensitive_post_parameters(), name="dispatch")
class CheckoutView(PaymentView):
    def post(self, request):
        services.require_customer(request.user)
        serializer = CheckoutInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "invalid_request", "detail": "Revisa los datos de la tarjeta.",
                             "field_errors": serializer.errors}, status=400)
        try:
            key = UUID(request.headers.get("Idempotency-Key", ""))
        except (ValueError, TypeError):
            raise PaymentError("invalid_request", "Se requiere una clave de operación UUID.", 400)
        try:
            result = services.execute_checkout(
                user=request.user, operation_key=key,
                quote_id=serializer.validated_data["quote_id"],
                card_data=serializer.validated_data["card"],
            )
        except (PaymentError, SubscriptionError):
            raise
        except Exception:
            # No exponer datos del formulario en una página técnica ni fingir rechazo bancario.
            raise PaymentError("payment_service_unavailable", "No se pudo completar la operación. Consulta su estado antes de reintentar.", 503) from None
        return Response(result)


class OperationResultView(PaymentView):
    def get(self, request, operation_key):
        return Response(services.get_operation_result(user=request.user, operation_key=operation_key))


class PaymentResultView(PaymentView):
    def get(self, request, payment_id):
        return Response(services.get_payment_result(user=request.user, payment_id=payment_id))
