# subscriptions/serializers.py
from rest_framework import serializers


class PreferenceInputSerializer(serializers.Serializer):
    plan_version_id = serializers.IntegerField()