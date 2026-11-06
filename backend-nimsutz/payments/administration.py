"""Lecturas comerciales de administración. Sin modelos espejo ni contenido de archivos."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from files.models import File, QuotaReservation
from payments.models import Payment
from subscriptions.coverage import period_at
from subscriptions.models import CoveragePeriod, Subscription

from .read_serializers import (
    AdministrationPaymentDetailSerializer,
    AdministrationPaymentSummarySerializer,
    AdministrationHistoryQuerySerializer,
)

GUATEMALA = ZoneInfo("America/Guatemala")


class ActiveAdministrator(IsAuthenticated):
    """Permiso compartido provisionalmente definido por las reglas de cuentas."""
    def has_permission(self, request, view):
        user = request.user
        return bool(super().has_permission(request, view) and user.is_authenticated
                    and user.role == User.Role.ADMINISTRADOR and user.email_verified
                    and user.account_status == User.AccountStatus.ACTIVE)


class MetricsQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate_date_to(self, value):
        if value == datetime.max.date():
            raise serializers.ValidationError("Usa una fecha final anterior al 31 de diciembre de 9999.")
        return value

    def validate(self, attrs):
        today = timezone.now().astimezone(GUATEMALA).date()
        attrs.setdefault("date_from", today.replace(day=1))
        attrs.setdefault("date_to", today)
        if attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": "La fecha final no puede ser anterior a la inicial."})
        if attrs["date_to"] > today:
            raise serializers.ValidationError({"date_to": "La fecha final no puede ser futura."})
        return attrs


def day_bounds(date_from, date_to):
    lower = datetime.combine(date_from, time.min, tzinfo=GUATEMALA)
    upper = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=GUATEMALA)
    return lower, upper


def collect_metrics(*, date_from, date_to, at=None):
    """Calcular cada agregado en su origen para que relaciones 1:N no multipliquen sumas."""
    reference = at or timezone.now()
    counts = User.objects.filter(role=User.Role.CLIENTE).aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(account_status=User.AccountStatus.ACTIVE)),
        pending=Count("id", filter=Q(account_status=User.AccountStatus.PENDING_VERIFICATION)),
        suspended=Count("id", filter=Q(account_status=User.AccountStatus.SUSPENDED)),
    )
    active_subscriptions = 0
    # Lee periodos comerciales vigentes y excluye selecciones pendientes o cobertura futura.
    for sub in Subscription.objects.filter(user__role=User.Role.CLIENTE).select_related(
        "plan_version__plan"
    ).prefetch_related("coverage_history").iterator(chunk_size=200):
        if sub.status == Subscription.Status.PENDING:
            continue
        if sub.coverage_history.exists():
            active_subscriptions += int(period_at(sub, reference) is not None)
        else:
            # Compatibilidad con contratos históricos aún no materializados en CoveragePeriod.
            active_subscriptions += int(
                sub.started_at is not None and sub.started_at <= reference
                and (sub.expires_at is None or sub.expires_at > reference)
            )

    file_counts = File.objects.filter(
        status__in=(File.Status.AVAILABLE, File.Status.TRASHED)
    ).aggregate(
        total=Count("id"),
        in_trash=Count("id", filter=Q(status=File.Status.TRASHED)),
    )
    # Una reserva confirmada cuenta si aún representa un archivo no borrado definitivamente.
    storage_bytes = QuotaReservation.objects.filter(
        status=QuotaReservation.Status.CONFIRMED,
        file__isnull=False,
        file__status__in=(File.Status.AVAILABLE, File.Status.TRASHED),
    ).aggregate(total=Sum("reserved_bytes"))["total"] or 0

    lower, upper = day_bounds(date_from, date_to)
    payments = Payment.objects.filter(created_at__gte=lower, created_at__lt=upper)
    payment_totals = payments.aggregate(
        approved_count=Count("id", filter=Q(status=Payment.Status.APPROVED)),
        rejected_count=Count("id", filter=Q(status=Payment.Status.REJECTED)),
        approved_amount=Sum("amount", filter=Q(status=Payment.Status.APPROVED)),
    )
    approved_currency = (payments.filter(status=Payment.Status.APPROVED)
                         .order_by("currency").values_list("currency", flat=True).first()) or "GTQ"
    return {
        "as_of": reference.isoformat(),
        "period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        "clients": {"total": counts["total"], "by_status": {
            "activa": counts["active"], "pendiente_verificacion": counts["pending"], "suspendida": counts["suspended"],
        }},
        "active_subscriptions": active_subscriptions,
        "files": file_counts,
        "storage": {"used_bytes": storage_bytes},
        "payments": {
            "approved_count": payment_totals["approved_count"],
            "rejected_count": payment_totals["rejected_count"],
            "approved_amount": f'{payment_totals["approved_amount"] or 0:.2f}',
            "currency": approved_currency,
        },
    }


class MetricsView(APIView):
    permission_classes = [ActiveAdministrator]

    def get(self, request):
        query = MetricsQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"code": "invalid_request", "detail": "Revisa el periodo de métricas.",
                             "field_errors": query.errors}, status=400)
        return Response(collect_metrics(**query.validated_data))


class AdministrationPaymentListView(APIView):
    permission_classes = [ActiveAdministrator]

    def get(self, request):
        query = AdministrationHistoryQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"code": "invalid_request", "detail": "Revisa los filtros del historial.",
                             "field_errors": query.errors}, status=400)
        params = query.validated_data
        queryset = Payment.objects.select_related("owner").order_by("-created_at", "-id")
        if "client_id" in params:
            queryset = queryset.filter(owner_id=params["client_id"])
        if "status" in params:
            queryset = queryset.filter(status=params["status"])
        if "operation" in params:
            queryset = queryset.filter(operation=params["operation"])
        lower, upper = query.created_at_bounds()
        if lower:
            queryset = queryset.filter(created_at__gte=lower)
        if upper:
            queryset = queryset.filter(created_at__lt=upper)
        paginator = Paginator(queryset, params["page_size"])
        try:
            page = paginator.page(params["page"])
        except EmptyPage:
            page = paginator.page(1) if paginator.count == 0 and params["page"] == 1 else None
        if page is None:
            return Response({"code": "not_found", "detail": "Esa página del historial no existe.", "field_errors": {}}, status=404)
        def link(number):
            kept = {key: request.query_params[key] for key in request.query_params
                    if key != "page" and key in AdministrationHistoryQuerySerializer().fields}
            from django.utils.http import urlencode
            return f"{request.path}?{urlencode({**kept, 'page': number})}"
        return Response({
            "count": paginator.count,
            "next": link(page.next_page_number()) if page.has_next() else None,
            "previous": link(page.previous_page_number()) if page.has_previous() else None,
            "results": AdministrationPaymentSummarySerializer(page.object_list, many=True).data,
        })


class AdministrationPaymentDetailView(APIView):
    permission_classes = [ActiveAdministrator]

    def get(self, request, payment_id):
        payment = (Payment.objects.select_related("owner").prefetch_related("lines")
                   .filter(pk=payment_id).first())
        if payment is None:
            return Response({"code": "not_found", "detail": "No se encontró el pago.", "field_errors": {}}, status=404)
        return Response(AdministrationPaymentDetailSerializer(payment).data)
