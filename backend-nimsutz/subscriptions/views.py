# subscriptions/views.py
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import UserSerializer

from . import services
from .errors import SubscriptionError
from .overview import build_account_overview
from .serializers import PlanVersionInputSerializer, QuoteCreateSerializer


def _error(error):
    return Response(error.as_body(), status=error.http_status)


class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"plans": services.list_catalog()})


class PreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"preference": services.get_preference(request.user)})

    def put(self, request):
        serializer = PlanVersionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Datos inválidos.", "code": "invalid_request", "field_errors": serializer.errors},
                status=400,
            )
        try:
            services.set_preference(
                user=request.user, plan_version_id=serializer.validated_data["plan_version_id"]
            )
        except SubscriptionError as e:
            return _error(e)
        return Response({"preference": services.get_preference(request.user)})


class CurrentSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = services.get_active_subscription(request.user)
        return Response({
            "subscription": services.subscription_payload(sub) if sub else None,
            "next_cycle": services.next_cycle_payload(sub),
            "scheduled_change": services.scheduled_change_payload(request.user),
            "allowed_actions": services.get_allowed_actions(sub, request.user),
        })


class ActivateFreeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PlanVersionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Datos inválidos.", "code": "invalid_request", "field_errors": serializer.errors},
                status=400,
            )
        try:
            subscription, created = services.activate_free(
                user=request.user, plan_version_id=serializer.validated_data["plan_version_id"]
            )
        except SubscriptionError as e:
            return _error(e)
        return Response(
            {"subscription": services.subscription_payload(subscription)},
            status=201 if created else 200,
        )


class AccountOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = build_account_overview(request.user)
        return Response({"user": UserSerializer(request.user).data, **data})


# ---------------------------------------------------------------------------
# NUEVAS VISTAS: COTIZACIONES Y CAMBIOS PROGRAMADOS (Contratos 7.3 y 7.4)
# ---------------------------------------------------------------------------

class QuoteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = QuoteCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Datos inválidos.", "code": "invalid_request", "field_errors": serializer.errors},
                status=400,
            )
        try:
            quote = services.prepare_quote(
                user=request.user,
                operation=serializer.validated_data["operation"],
                plan_version_id=serializer.validated_data.get("plan_version_id"),
            )
        except SubscriptionError as e:
            return _error(e)
        return Response({"quote": services.quote_payload(quote)}, status=status.HTTP_201_CREATED)


class QuoteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quote_id):
        try:
            quote = services.get_quote(user=request.user, quote_id=quote_id)
        except SubscriptionError as e:
            return _error(e)
        return Response({"quote": services.quote_payload(quote)})


class QuoteConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quote_id):
        try:
            scheduled, sub = services.confirm_scheduled_quote(
                user=request.user, quote_id=quote_id
            )
        except SubscriptionError as e:
            return _error(e)
        return Response({
            "scheduled_change": services.scheduled_change_payload(request.user),
            "subscription": services.subscription_payload(sub),
        })


class ScheduledChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        services.cancel_scheduled_change(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
