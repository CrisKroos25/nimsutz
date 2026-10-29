# payments/read_views.py
"""Consulta del historial de pagos propios (solo lectura, seccion 7.7)."""
from django.core.paginator import EmptyPage, Paginator
from django.utils.http import urlencode
from rest_framework.response import Response

from . import services
from .errors import PaymentError
from .models import Payment
from .read_serializers import HistoryQuerySerializer, PaymentDetailSerializer, PaymentSummarySerializer
from .views import PaymentView


class PaymentHistoryView(PaymentView):
    """GET /api/payments/ con filtros opcionales. Solo expone GET: un POST, PUT,
    PATCH o DELETE responde 405, asi que ningun resultado de pago se puede alterar."""

    def get(self, request):
        services.require_customer(request.user)
        query = HistoryQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"code": "invalid_request", "detail": "Revisa los filtros del historial.",
                             "field_errors": query.errors}, status=400)
        params = query.validated_data
        # El filtro por propietario sale siempre de la sesion, nunca de la URL.
        queryset = Payment.objects.filter(owner=request.user).order_by("-created_at", "-id")
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
            if params["page"] == 1:  # historial vacio: no es un error
                return Response({"count": 0, "next": None, "previous": None, "results": []})
            raise PaymentError("not_found", "Esa pagina del historial no existe.", 404)

        def link(number):
            kept = {key: request.query_params[key] for key in request.query_params
                    if key not in ("page",) and key in HistoryQuerySerializer().fields}
            return f"{request.path}?{urlencode({**kept, 'page': number})}"

        return Response({
            "count": paginator.count,
            "next": link(page.next_page_number()) if page.has_next() else None,
            "previous": link(page.previous_page_number()) if page.has_previous() else None,
            "results": PaymentSummarySerializer(page.object_list, many=True).data,
        })


class PaymentHistoryDetailView(PaymentView):
    """GET /api/payments/<id>/. Un pago de otra cuenta responde 404."""

    def get(self, request, payment_id):
        services.require_customer(request.user)
        payment = (Payment.objects.filter(owner=request.user, pk=payment_id)
                   .prefetch_related("lines").first())
        if payment is None:
            raise PaymentError("not_found", "No se encontró el pago.", 404)
        return Response(PaymentDetailSerializer(payment).data)
