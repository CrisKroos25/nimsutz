from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditEvent
from .services import record_event

GT = ZoneInfo("America/Guatemala")


class AuditApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(
            email="admin-api@example.test", name="Admin", password="secret")
        cls.client_user = User.objects.create_user(
            email="cliente-api@example.test", name="Cliente", password="secret",
            email_verified=True, account_status=User.AccountStatus.ACTIVE)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def event(self, **kw):
        data = dict(actor=self.admin, action="client.suspended", entity_type="client",
                    entity_id="3", result="success", metadata={"new_status": "suspendida"})
        data.update(kw)
        return record_event(**data)

    def test_list_shape_order_and_pagination(self):
        first, second, third = self.event(), self.event(result="no_change"), self.event(entity_id="9")
        response = self.api.get("/api/administration/audit/?page_size=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual([e["id"] for e in response.data["results"]], [third.id, second.id])
        self.assertIsNotNone(response.data["next"])
        item = response.data["results"][0]
        self.assertEqual(set(item), {"id", "actor", "action", "entity_type", "entity_id",
                                     "result", "created_at", "metadata"})
        self.assertEqual(item["actor"], {"id": self.admin.pk, "label": "admin-api@example.test"})

    def test_filters(self):
        self.event()
        self.event(action="plan.deactivated", entity_type="plan", entity_id="2", result="rejected",
                   metadata={"reason_code": "in_use"})
        def count(query):
            return self.api.get(f"/api/administration/audit/?{query}").data["count"]
        self.assertEqual(count("action=plan.deactivated"), 1)
        self.assertEqual(count("entity_type=client&entity_id=3"), 1)
        self.assertEqual(count("result=rejected"), 1)
        self.assertEqual(count(f"actor_id={self.admin.pk}"), 2)
        self.assertEqual(count("actor_id=99999"), 0)

    def test_date_filters_use_guatemala_days(self):
        # 2026-11-01 23:30 en Guatemala = 2026-11-02 05:30 UTC
        late = self.event()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("UPDATE audit_auditevent SET created_at=%s WHERE id=%s",
                           [datetime(2026, 11, 1, 23, 30, tzinfo=GT).astimezone(ZoneInfo("UTC")).replace(tzinfo=None), late.pk])
        day1 = self.api.get("/api/administration/audit/?date_from=2026-11-01&date_to=2026-11-01")
        day2 = self.api.get("/api/administration/audit/?date_from=2026-11-02&date_to=2026-11-02")
        self.assertEqual(day1.data["count"], 1)
        self.assertEqual(day2.data["count"], 0)

    def test_invalid_filters_and_missing_page(self):
        bad = self.api.get("/api/administration/audit/?action=nope&date_from=2026-11-05&date_to=2026-11-01")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.data["code"], "invalid_request")
        self.assertIn("action", bad.data["field_errors"])
        self.event()
        self.assertEqual(self.api.get("/api/administration/audit/?page=5").status_code, 404)

    def test_detail_and_404(self):
        event = self.event()
        self.assertEqual(self.api.get(f"/api/administration/audit/{event.id}/").data["id"], event.id)
        missing = self.api.get("/api/administration/audit/99999/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.data["code"], "not_found")

    def test_event_persists_after_entity_deletion(self):
        victim = get_user_model().objects.create_user(email="gone@example.test", name="X", password="secret")
        event = self.event(entity_id=str(victim.pk))
        victim.delete()
        self.assertEqual(self.api.get(f"/api/administration/audit/{event.id}/").status_code, 200)

    def test_no_write_methods(self):
        event = self.event()
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(self.api, method)("/api/administration/audit/").status_code, 405)
            self.assertEqual(getattr(self.api, method)(f"/api/administration/audit/{event.id}/").status_code, 405)

    def test_client_is_denied_and_denial_is_audited(self):
        self.api.force_authenticate(self.client_user)
        response = self.api.get("/api/administration/audit/")
        self.assertEqual(response.status_code, 403)
        denied = AuditEvent.objects.get(action="administration.access_denied")
        self.assertEqual(denied.actor_ref, self.client_user.pk)
        self.assertEqual(denied.result, "rejected")
        self.assertEqual(denied.entity_id, "/api/administration/audit/")
        # El rechazo no expone eventos
        self.assertNotIn("results", response.data)

    def test_anonymous_is_denied_without_event(self):
        self.api.force_authenticate(None)
        self.assertIn(self.api.get("/api/administration/audit/").status_code, (401, 403))
        self.assertEqual(AuditEvent.objects.count(), 0)
