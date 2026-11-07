from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = ("id", "actor", "action", "entity_type", "entity_id",
                  "result", "created_at", "metadata")
        read_only_fields = fields

    def get_actor(self, obj):
        if obj.actor_ref is None and not obj.actor_label:
            return None
        return {"id": obj.actor_ref, "label": obj.actor_label}
