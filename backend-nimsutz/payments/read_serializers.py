# payments/read_serializers.py
"""Contrato de lectura del historial de pagos (secciones 7.7 y 7.8 de la guia).

Todo es de solo lectura: ningun serializer de este archivo recibe ni guarda datos.
Nunca se exponen operation_key, quote_id, request_digest ni result_snapshot.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from rest_framework import serializers

from .models import Payment, PaymentDetail

GUATEMALA = ZoneInfo("America/Guatemala")
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
OPERATIONS = ("contract", "renew", "change")


class PaymentSummarySerializer(serializers.ModelSerializer):
    """Mismos campos publicos del objeto payment del checkout."""
    reference = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ("id", "reference", "status", "reason_code", "operation", "amount",
                  "currency", "created_at", "card_last4")
        read_only_fields = fields

    def get_reference(self, payment):
        return str(payment.reference)

    def get_amount(self, payment):
        # Dinero como cadena decimal de dos posiciones, nunca float.
        return f"{payment.amount:.2f}"


class PaymentLineSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = PaymentDetail
        fields = ("code", "description", "amount")
        read_only_fields = fields

    def get_amount(self, line):
        return f"{line.amount:.2f}"


class PaymentDetailSerializer(PaymentSummarySerializer):
    """Detalle: agrega las lineas y el plan tal como se contrato al operar."""
    lines = PaymentLineSerializer(many=True, read_only=True)
    plan = serializers.SerializerMethodField()

    class Meta(PaymentSummarySerializer.Meta):
        fields = PaymentSummarySerializer.Meta.fields + ("lines", "plan")
        read_only_fields = fields

    def get_plan(self, payment):
        snapshot = payment.plan_snapshot if isinstance(payment.plan_snapshot, dict) else {}
        return {key: snapshot.get(key) for key in ("plan_code", "version_id", "name", "capacity_bytes")}


class HistoryQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in Payment.Status.choices], required=False)
    operation = serializers.ChoiceField(choices=OPERATIONS, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.IntegerField(min_value=1, required=False, default=DEFAULT_PAGE_SIZE)

    def validate_page_size(self, value):
        return min(value, MAX_PAGE_SIZE)

    def validate_date_to(self, value):
        # El límite superior exclusivo necesita el día siguiente representable.
        if value.year == 9999 and value.month == 12 and value.day == 31:
            raise serializers.ValidationError("Usa una fecha final anterior al 31 de diciembre de 9999.")
        return value

    def validate(self, attrs):
        start, end = attrs.get("date_from"), attrs.get("date_to")
        if start and end and start > end:
            raise serializers.ValidationError({"date_to": "La fecha final no puede ser anterior a la inicial."})
        return attrs

    def created_at_bounds(self):
        """Fechas de calendario en America/Guatemala; date_to incluye todo ese dia."""
        data = self.validated_data
        lower = upper = None
        if data.get("date_from"):
            lower = datetime.combine(data["date_from"], time.min, tzinfo=GUATEMALA)
        if data.get("date_to"):
            upper = datetime.combine(data["date_to"] + timedelta(days=1), time.min, tzinfo=GUATEMALA)
        return lower, upper
