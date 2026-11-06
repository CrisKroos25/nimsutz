from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase
from rest_framework.test import APIClient


class AdministrationClientsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(email="admin-m18@example.test", name="Admin", password="secret")
        cls.client_user = User.objects.create_user(email="client-m18@example.test", name="Cliente Uno",
            password="secret", email_verified=True, account_status=User.AccountStatus.ACTIVE)
        cls.pending = User.objects.create_user(email="pending-m18@example.test", name="Pendiente",
            email_verified=False, account_status=User.AccountStatus.PENDING_VERIFICATION)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_list_search_status_pagination_and_detail_exposes_no_file_content(self):
        response = self.api.get("/api/administration/clients/?search=CLIENTE&status=activa&page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(item["email"], self.client_user.email)
        self.assertIn("usage_bytes", item)
        self.assertIn("file_count", item)
        self.assertIn("coverage_end", item)
        self.assertNotIn("files", item)
        detail = self.api.get(f"/api/administration/clients/{self.client_user.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["plan"], None)
        self.assertEqual(self.api.get(f"/api/administration/clients/{self.admin.pk}/").status_code, 404)

    def test_api_denies_client_and_admin_without_verified_active_status(self):
        for user in (self.client_user,):
            self.api.force_authenticate(user)
            self.assertEqual(self.api.get("/api/administration/clients/").status_code, 403)
        for changes in ({"email_verified": False}, {"account_status": UserStatus.SUSPENDED}):
            get_user_model().objects.filter(pk=self.admin.pk).update(**changes)
            self.admin.refresh_from_db()
            self.api.force_authenticate(self.admin)
            self.assertEqual(self.api.get("/api/administration/clients/").status_code, 403)
            get_user_model().objects.filter(pk=self.admin.pk).update(
                email_verified=True, account_status=UserStatus.ACTIVE)

    @patch("accounts.services._record_account_event")
    def test_suspend_invalidates_old_session_and_reactivation_does_not_restore_it(self, record_event):
        old_client = APIClient()
        old_client.force_login(self.client_user)
        old_key = old_client.session.session_key
        self.api.force_authenticate(self.admin)
        result = self.api.post(f"/api/administration/clients/{self.client_user.pk}/suspend/", {}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["changed"])
        self.assertTrue(result.data["sessions_invalidated"])
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.assertIsNone(old_client.get("/api/auth/session/").data["user"])
        result = self.api.post(f"/api/administration/clients/{self.client_user.pk}/reactivate/", {}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["client"]["account_status"], UserStatus.ACTIVE)
        self.assertIsNone(old_client.get("/api/auth/session/").data["user"])
        self.assertEqual([call.kwargs["action"] for call in record_event.call_args_list],
                         ["client.suspended", "client.reactivated"])

    @patch("accounts.services._record_account_event")
    def test_reactivation_keeps_unverified_user_pending_and_rejects_self_or_admin_target(self, record_event):
        self.pending.account_status = UserStatus.SUSPENDED
        self.pending.save(update_fields=["account_status"])
        result = self.api.post(f"/api/administration/clients/{self.pending.pk}/reactivate/", {}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["client"]["account_status"], UserStatus.PENDING)
        self.assertEqual(self.api.post(f"/api/administration/clients/{self.admin.pk}/suspend/", {}, format="json").status_code, 404)
        self.assertEqual(self.api.post(f"/api/administration/clients/{self.admin.pk}/reactivate/", {}, format="json").status_code, 404)

    @patch("accounts.services._record_account_event")
    def test_repeated_suspend_is_no_change_without_claiming_session_invalidation(self, record_event):
        self.client_user.account_status = UserStatus.SUSPENDED
        self.client_user.save(update_fields=["account_status"])
        result = self.api.post(f"/api/administration/clients/{self.client_user.pk}/suspend/", {}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.data["changed"])
        self.assertFalse(result.data["sessions_invalidated"])
        self.assertEqual(record_event.call_args.kwargs["result"], "no_change")


class UserStatus:
    ACTIVE = "activa"
    SUSPENDED = "suspendida"
    PENDING = "pendiente_verificacion"
