# accounts/tests.py
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.core import mail
from django.utils import timezone

from datetime import timedelta

from .models import PasswordResetToken

@override_settings(SIMULATED_AUTH_ENABLED=True, SIMULATED_USER_ID=1)
class DemoSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            name="Usuario Demo",
            email="demo@example.test",
            password="test-password",
            account_status=get_user_model().AccountStatus.ACTIVE,
            email_verified=True,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get("/api/auth/session/").json()["csrfToken"]

    def sign_in(self, **credentials):
        return self.client.post(
            "/api/auth/login/",
            data=json.dumps({"email": "demo@example.test", "password": "test-password", **credentials}),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.token,
        )

    def test_anonymous_session_and_private_api(self):
        self.assertIsNone(self.client.get("/api/auth/session/").json()["user"])
        for path in ["/api/files/", "/api/folders/"]:
            self.assertEqual(self.client.get(path).status_code, 403)

    def test_login_persists_and_logout_revokes_session(self):
        response = self.sign_in()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/session/").json()["user"]["id"], self.user.id)
        self.assertEqual(self.client.get("/api/folders/").status_code, 200)
        response = self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=response.json()["csrfToken"])
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["user"])
        self.assertEqual(self.client.get("/api/folders/").status_code, 403)

    def test_wrong_credentials(self):
        for credentials in [{"password": "wrong"}, {"email": "other@example.test"}]:
            self.assertEqual(self.sign_in(**credentials).status_code, 401)
        self.assertEqual(self.client.get("/api/files/").status_code, 403)

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.sign_in().status_code, 401)

    def test_other_account_rejected(self):
        get_user_model().objects.create_user(name="Otro", email="other@example.test", password="test-password")
        self.assertEqual(self.sign_in(email="other@example.test").status_code, 401)

    def test_csrf_required_for_login_logout_and_file_mutations(self):
        self.assertEqual(self.client.post("/api/auth/login/").status_code, 403)
        self.sign_in()
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 403)
        self.assertEqual(self.client.post("/api/folders/", {"name": "blocked"}).status_code, 403)

    def test_malformed_body(self):
        for body in ["null", "[]", "{", '{"email": 123, "password": true}']:
            response = self.client.post("/api/auth/login/", body, content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
            self.assertEqual(response.status_code, 400)


class AdminActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            name="Admin", email="admin@example.test", password="test-password",
            role=User.Role.ADMINISTRADOR, account_status=User.AccountStatus.ACTIVE,
            email_verified=True,
        )
        cls.client_user = User.objects.create_user(
            name="Cliente", email="cliente@example.test", password="test-password",
            account_status=User.AccountStatus.ACTIVE, email_verified=True,
        )

    def login_as(self, email):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/auth/session/").json()["csrfToken"]
        response = client.post(
            "/api/auth/login/",
            data=json.dumps({"email": email, "password": "test-password"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        return client, response.json()["csrfToken"]

    def test_non_admin_cannot_suspend(self):
        client, token = self.login_as("cliente@example.test")
        response = client.post(
            f"/api/admin/users/{self.admin.pk}/suspend/", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_suspend_and_session_is_killed(self):
        target_client, target_token = self.login_as("cliente@example.test")
        self.assertEqual(target_client.get("/api/folders/").status_code, 200)

        admin_client, admin_token = self.login_as("admin@example.test")
        response = admin_client.post(
            f"/api/admin/users/{self.client_user.pk}/suspend/", HTTP_X_CSRFTOKEN=admin_token
        )
        self.assertEqual(response.status_code, 200)

        # La MISMA sesión del cliente, ya iniciada antes de la suspensión,
        # debe quedar invalidada en la siguiente petición (RN-E1-13).
        self.assertEqual(target_client.get("/api/folders/").status_code, 403)

    def test_cannot_suspend_self_or_another_admin(self):
        admin_client, admin_token = self.login_as("admin@example.test")
        self.assertEqual(
            admin_client.post(f"/api/admin/users/{self.admin.pk}/suspend/", HTTP_X_CSRFTOKEN=admin_token).status_code,
            400,
        )

    def test_suspend_is_idempotent(self):
        admin_client, admin_token = self.login_as("admin@example.test")
        for _ in range(2):
            response = admin_client.post(
                f"/api/admin/users/{self.client_user.pk}/suspend/", HTTP_X_CSRFTOKEN=admin_token
            )
            self.assertEqual(response.status_code, 200)

    def test_reactivate_requires_suspended_status(self):
        admin_client, admin_token = self.login_as("admin@example.test")
        response = admin_client.post(
            f"/api/admin/users/{self.client_user.pk}/reactivate/", HTTP_X_CSRFTOKEN=admin_token
        )
        self.assertEqual(response.status_code, 400)  # estaba activa, no suspendida

class PasswordResetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            name="Ana Prueba",
            email="ana@example.test",
            password="old-password-123",
            account_status=User.AccountStatus.ACTIVE,
            email_verified=True,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/auth/session/").json()["csrfToken"]

    def post(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )

    def request_reset(self, email="ana@example.test"):
        return self.post("/api/auth/password-reset/", {"email": email})

    def confirm(self, token, new_password="new-password-123"):
        return self.post(
            "/api/auth/password-reset/confirm/",
            {"token": token, "new_password": new_password},
        )

    def test_request_sends_email_and_creates_token(self):
        response = self.request_reset()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@example.test"])
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertIn(token.token, mail.outbox[0].body)

    def test_request_unknown_email_does_not_reveal_anything(self):
        known = self.request_reset()
        unknown = self.request_reset("nadie@example.test")
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.json(), known.json())
        self.assertEqual(len(mail.outbox), 1)  # solo el de la cuenta real
        self.assertEqual(PasswordResetToken.objects.count(), 1)

    def test_new_request_invalidates_previous_token(self):
        self.request_reset()
        first = PasswordResetToken.objects.get(user=self.user)
        self.request_reset()
        first.refresh_from_db()
        self.assertIsNotNone(first.used_at)
        self.assertEqual(self.confirm(first.token).status_code, 401)

    def test_confirm_changes_password_and_allows_login(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(self.confirm(token.token).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password-123"))
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_confirm_token_cannot_be_reused(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(self.confirm(token.token).status_code, 200)
        self.assertEqual(self.confirm(token.token, "other-password-1").status_code, 401)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password-123"))

    def test_confirm_invalid_token(self):
        self.assertEqual(self.confirm("token-que-no-existe").status_code, 401)

    def test_confirm_expired_token(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        token.expires_at = timezone.now() - timedelta(minutes=1)
        token.save(update_fields=["expires_at"])
        self.assertEqual(self.confirm(token.token).status_code, 401)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-password-123"))

    def test_confirm_rejects_short_password(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(self.confirm(token.token, "corta").status_code, 400)

    def test_reset_does_not_change_account_status_or_role(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.confirm(token.token)
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, "activa")
        self.assertEqual(self.user.role, "cliente")
        self.assertTrue(self.user.email_verified)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/api/auth/password-reset/",
            data=json.dumps({"email": "ana@example.test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)