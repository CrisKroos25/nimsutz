"""Consultas y operaciones de clientes para el módulo administrativo M18."""
from zoneinfo import ZoneInfo

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from files.models import File, QuotaReservation
from subscriptions.coverage import period_at
from subscriptions.models import CoveragePeriod, Subscription

from . import services
from .models import User

GUATEMALA = ZoneInfo("America/Guatemala")


class ActiveAdministrator(IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        return bool(super().has_permission(request, view) and user.is_authenticated
                    and user.role == User.Role.ADMINISTRADOR and user.email_verified
                    and user.account_status == User.AccountStatus.ACTIVE)


class ClientQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=254)
    status = serializers.ChoiceField(required=False, choices=User.AccountStatus.choices)
    plan_code = serializers.SlugField(required=False, max_length=30)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, default=20)

    def validate_page_size(self, value):
        return min(value, 100)


def _client_payload(user, at=None):
    reference = at or timezone.now()
    sub = (Subscription.objects.filter(user=user)
           .select_related("plan_version__plan", "next_cycle_plan_version__plan").first())
    period = None
    if sub and sub.status != Subscription.Status.PENDING:
        period = period_at(sub, reference) if sub.coverage_history.exists() else None
        if period is None and not sub.coverage_history.exists() and sub.started_at and sub.started_at <= reference \
                and (sub.expires_at is None or sub.expires_at > reference):
            version = sub.plan_version
            coverage_end = sub.coverage_end or sub.expires_at
        elif period is not None:
            version = period.plan_version
            coverage_end = sub.coverage_end or period.ends_at
        else:
            version = None
            coverage_end = None
    else:
        version = None
        coverage_end = None
    usage = QuotaReservation.objects.filter(
        owner=user, status=QuotaReservation.Status.CONFIRMED, file__isnull=False,
        file__status__in=(File.Status.AVAILABLE, File.Status.TRASHED),
    ).aggregate(total=Sum("reserved_bytes"))["total"] or 0
    file_count = File.objects.filter(
        owner=user, status__in=(File.Status.AVAILABLE, File.Status.TRASHED)
    ).count()
    return {
        "id": user.pk,
        "name": user.name,
        "email": user.email,
        "account_status": user.account_status,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "plan": ({"code": version.plan.code, "name": version.name or version.plan.name,
                  "version_id": version.pk} if version else None),
        "coverage_end": coverage_end.isoformat() if coverage_end else None,
        "usage_bytes": usage,
        "file_count": file_count,
    }


def _admin_error(code, detail, status_code, field_errors=None):
    return Response({"code": code, "detail": detail, "field_errors": field_errors or {}}, status=status_code)


class ClientListView(APIView):
    permission_classes = [ActiveAdministrator]

    def get(self, request):
        query = ClientQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _admin_error("invalid_request", "Revisa los filtros de clientes.", 400, query.errors)
        params = query.validated_data
        users = User.objects.filter(role=User.Role.CLIENTE).order_by("-created_at", "-id")
        if params.get("search"):
            search = params["search"].strip()
            users = users.filter(Q(name__icontains=search) | Q(email__icontains=search))
        if params.get("status"):
            users = users.filter(account_status=params["status"])
        if params.get("plan_code"):
            now = timezone.now()
            in_period_ids = CoveragePeriod.objects.filter(
                subscription__user__role=User.Role.CLIENTE,
                state=CoveragePeriod.State.VALID,
                starts_at__lte=now,
                plan_version__plan__code=params["plan_code"],
            ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).values_list(
                "subscription__user_id", flat=True
            )
            legacy_ids = Subscription.objects.filter(
                user__role=User.Role.CLIENTE,
                plan_version__plan__code=params["plan_code"],
                status=Subscription.Status.ACTIVE,
                started_at__lte=now,
                coverage_history__isnull=True,
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).values_list("user_id", flat=True)
            users = users.filter(Q(pk__in=in_period_ids) | Q(pk__in=legacy_ids)).distinct()
        paginator = Paginator(users, params["page_size"])
        try:
            page = paginator.page(params["page"])
        except EmptyPage:
            if paginator.count == 0 and params["page"] == 1:
                return Response({"count": 0, "next": None, "previous": None, "results": []})
            return _admin_error("not_found", "Esa página de clientes no existe.", 404)

        def link(number):
            from django.utils.http import urlencode
            kept = {key: request.query_params[key] for key in ClientQuerySerializer().fields
                    if key in request.query_params and key != "page"}
            return f"{request.path}?{urlencode({**kept, 'page': number})}"

        return Response({
            "count": paginator.count,
            "next": link(page.next_page_number()) if page.has_next() else None,
            "previous": link(page.previous_page_number()) if page.has_previous() else None,
            "results": [_client_payload(user) for user in page.object_list],
        })


class ClientDetailView(APIView):
    permission_classes = [ActiveAdministrator]

    def get(self, request, client_id):
        user = User.objects.filter(pk=client_id, role=User.Role.CLIENTE).first()
        if user is None:
            return _admin_error("not_found", "No se encontró el cliente.", 404)
        return Response(_client_payload(user))


def _change_account(request, client_id, *, reactivate):
    target = User.objects.filter(pk=client_id, role=User.Role.CLIENTE).first()
    if target is None:
        return _admin_error("not_found", "No se encontró el cliente.", 404)
    previous = target.account_status
    action = services.reactivate_account if reactivate else services.suspend_account
    try:
        target = action(actor=request.user, target=target)
    except services.AuthorizationError as exc:
        return _admin_error("forbidden", str(exc), 403)
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            # Negocio rechazado: persistir el evento una vez que el servicio revirtió su transacción.
            services._record_account_event(
                actor=request.user,
                action="client.reactivated" if reactivate else "client.suspended",
                target=target, result="rejected", metadata={"reason_code": "invalid_state"},
            )
            return _admin_error("invalid_state", "La cuenta no admite este cambio de estado.", 400)
        raise
    return Response({
        "client": _client_payload(target),
        "changed": bool(getattr(target, "_admin_changed", previous != target.account_status)),
        "sessions_invalidated": bool(getattr(target, "_sessions_invalidated", False)),
    })


class SuspendClientView(APIView):
    permission_classes = [ActiveAdministrator]

    def post(self, request, client_id):
        if request.data not in ({}, None):
            return _admin_error("invalid_request", "El cuerpo debe estar vacío.", 400)
        return _change_account(request, client_id, reactivate=False)


class ReactivateClientView(APIView):
    permission_classes = [ActiveAdministrator]

    def post(self, request, client_id):
        if request.data not in ({}, None):
            return _admin_error("invalid_request", "El cuerpo debe estar vacío.", 400)
        return _change_account(request, client_id, reactivate=True)
