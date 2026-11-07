from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase

from .models import AuditEvent
from .services import AuditError, record_event


class RecordEventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            email="admin-audit@example.test", name="Admin", password="secret")

    def record(self, **overrides):
        data = dict(actor=self.admin, action="client.suspended", entity_type="client",
                    entity_id="7", result="success",
                    metadata={"previous_status": "activa", "new_status": "suspendida"})
        data.update(overrides)
        return record_event(**data)

    def test_records_event_with_actor_label_and_string_entity_id(self):
        event = self.record(entity_id=7)
        self.assertEqual(event.entity_id, "7")
        self.assertEqual(event.actor_ref, self.admin.pk)
        self.assertEqual(event.actor_label, "admin-audit@example.test")
        self.assertEqual(event.metadata["new_status"], "suspendida")

    def test_actor_may_be_none(self):
        event = self.record(actor=None)
        self.assertIsNone(event.actor)
        self.assertIsNone(event.actor_ref)

    def test_rejects_unknown_action_result_and_empty_entity(self):
        for bad in ({"action": "x.y"}, {"result": "ok"}, {"entity_id": ""}, {"entity_type": ""}):
            with self.assertRaises(AuditError):
                self.record(**bad)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_metadata_only_allows_known_scalar_keys(self):
        for bad in ({"password": "x"}, {"reason_code": {"a": 1}}, {"reason_code": "x" * 101}, "texto"):
            with self.assertRaises(AuditError):
                self.record(metadata=bad)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_events_cannot_be_modified_or_deleted(self):
        event = self.record()
        event.result = "error"
        with self.assertRaises(PermissionError):
            event.save()
        with self.assertRaises(PermissionError):
            event.delete()
        with self.assertRaises(PermissionError):
            AuditEvent.objects.all().update(result="error")
        with self.assertRaises(PermissionError):
            AuditEvent.objects.all().delete()

    def test_event_survives_actor_deletion(self):
        user = get_user_model().objects.create_user(
            email="temp-admin@example.test", name="Temp", password="secret")
        event = self.record(actor=user)
        user.delete()
        event.refresh_from_db()
        self.assertIsNone(event.actor)
        self.assertIsNotNone(event.actor_ref)
        self.assertEqual(event.actor_label, "temp-admin@example.test")

    def test_failure_to_record_rolls_back_the_mutation(self):
        target = get_user_model().objects.create_user(
            email="target-audit@example.test", name="Cliente", password="secret")
        with self.assertRaises(AuditError):
            with transaction.atomic():
                target.name = "Cambiado"
                target.save()
                self.record(action="desconocida")
        target.refresh_from_db()
        self.assertEqual(target.name, "Cliente")
