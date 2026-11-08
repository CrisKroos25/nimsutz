from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.paginator import EmptyPage, Paginator
from django.utils.http import urlencode
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditEvent
from .permissions import AuditedActiveAdministrator
from .serializers import AuditEventSerializer
from .services import ACTIONS

GUATEMALA = ZoneInfo("America/Guatemala")


def _error(code, detail, status_code, field_errors=None):
    return Response({"code": code, "detail": detail, "field_errors": field_errors or {}},
                    status=status_code)


class AuditQuerySerializer(serializers.Serializer):
    actor_id = serializers.IntegerField(required=False, min_value=1)
    action = serializers.ChoiceField(required=False, choices=sorted(ACTIONS))
    entity_type = serializers.CharField(required=False, max_length=40)
    entity_id = serializers.CharField(required=False, max_length=64)
    result = serializers.ChoiceField(required=False, choices=AuditEvent.Result.choices)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, default=20)

    def validate_page_size(self, value):
        return min(value, 100)

    def validate(self, attrs):
        start, end = attrs.get("date_from"), attrs.get("date_to")
        if start and end and start > end:
            raise serializers.ValidationError({"date_to": "La fecha final no puede ser anterior a la inicial."})
        return attrs


class AuditEventListView(APIView):
    permission_classes = [AuditedActiveAdministrator]

    def get(self, request):
        query = AuditQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _error("invalid_request", "Revisa los filtros de auditoría.", 400, query.errors)
        params = query.validated_data
        events = AuditEvent.objects.all().order_by("-created_at", "-id")
        if "actor_id" in params:
            events = events.filter(actor_ref=params["actor_id"])
        for field in ("action", "entity_type", "entity_id", "result"):
            if field in params:
                events = events.filter(**{field: params[field]})
        if "date_from" in params:
            events = events.filter(
                created_at__gte=datetime.combine(params["date_from"], time.min, tzinfo=GUATEMALA))
        if "date_to" in params:
            events = events.filter(
                created_at__lt=datetime.combine(params["date_to"] + timedelta(days=1), time.min, tzinfo=GUATEMALA))
        paginator = Paginator(events, params["page_size"])
        try:
            page = paginator.page(params["page"])
        except EmptyPage:
            if paginator.count == 0 and params["page"] == 1:
                return Response({"count": 0, "next": None, "previous": None, "results": []})
            return _error("not_found", "Esa página de auditoría no existe.", 404)

        def link(number):
            kept = {key: request.query_params[key] for key in AuditQuerySerializer().fields
                    if key in request.query_params and key != "page"}
            return f"{request.path}?{urlencode({**kept, 'page': number})}"

        return Response({
            "count": paginator.count,
            "next": link(page.next_page_number()) if page.has_next() else None,
            "previous": link(page.previous_page_number()) if page.has_previous() else None,
            "results": AuditEventSerializer(page.object_list, many=True).data,
        })


class AuditEventDetailView(APIView):
    permission_classes = [AuditedActiveAdministrator]

    def get(self, request, event_id):
        event = AuditEvent.objects.filter(pk=event_id).first()
        if event is None:
            return _error("not_found", "No se encontró el evento de auditoría.", 404)
        return Response(AuditEventSerializer(event).data)
