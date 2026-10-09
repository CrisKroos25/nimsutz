# subscriptions/views.py
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import UserSerializer

from . import services
from .errors import SubscriptionError
from .overview import build_account_overview
from .serializers import PreferenceInputSerializer


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
        serializer = PreferenceInputSerializer(data=request.data)
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
        return Response({"subscription": services.subscription_payload(sub) if sub else None})


class ActivateFreeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription, created = services.activate_free(user=request.user)
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