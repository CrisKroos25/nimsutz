# subscriptions/serializers.py
from rest_framework import serializers
from .models import Quote


class PlanVersionInputSerializer(serializers.Serializer):
    plan_version_id = serializers.IntegerField(min_value=1)


class QuoteCreateSerializer(serializers.Serializer):
    operation = serializers.ChoiceField(choices=Quote.Operation.choices)
    plan_version_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class ScheduledConfirmationSerializer(serializers.Serializer):
    operation_key = serializers.UUIDField()
