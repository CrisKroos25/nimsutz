# subscriptions/serializers.py
from rest_framework import serializers


class PlanVersionInputSerializer(serializers.Serializer):
    plan_version_id = serializers.IntegerField(min_value=1)