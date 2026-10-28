# accounts/tests.py
import json
import smtplib

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.core import mail
from django.utils import timezone

from datetime import timedelta
from unittest import mock

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

    def test_old_session_does_not_revive_after_reactivation(self):
        target_client, _ = self.login_as("cliente@example.test")
        self.assertEqual(target_client.get("/api/folders/").status_code, 200)

        admin_client, admin_token = self.login_as("admin@example.test")
        admin_client.post(
            f"/api/admin/users/{self.client_user.pk}/suspend/", HTTP_X_CSRFTOKEN=admin_token
        )
        admin_client.post(
            f"/api/admin/users/{self.client_user.pk}/reactivate/", HTTP_X_CSRFTOKEN=admin_token
        )

        # El cliente nunca hizo una petición mientras estuvo suspendido,
        # así que solo la invalidación de sesiones impide que la cookie vieja funcione.
        self.assertEqual(target_client.get("/api/folders/").status_code, 403)

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

    def test_confirm_rejects_whitespace_only_password_without_consuming_token(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)

        response = self.confirm(token.token, "            ")

        self.assertEqual(response.status_code, 400)
        self.assertIn("solo espacios", str(response.json()["new_password"]))
        token.refresh_from_db()
        self.assertIsNone(token.used_at)

    def test_confirm_preserves_leading_and_trailing_password_spaces(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        new_password = "  New-P@ssword-493!  "

        response = self.confirm(token.token, new_password)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_confirm_rejects_password_similar_to_user_email(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)

        response = self.confirm(token.token, "ana@example.test")

        self.assertEqual(response.status_code, 400)
        token.refresh_from_db()
        self.assertIsNone(token.used_at)

    def test_reset_does_not_change_account_status_or_role(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.confirm(token.token)
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, "activa")
        self.assertEqual(self.user.role, "cliente")
        self.assertTrue(self.user.email_verified)

    def test_request_reports_email_provider_failure(self):
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
            with self.assertLogs("accounts.emails", level="ERROR"):
                response = self.request_reset()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "email_delivery_failed")
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.user).count(), 1)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/api/auth/password-reset/",
            data=json.dumps({"email": "ana@example.test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_confirm_rejects_common_password_and_keeps_token_usable(self):
        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(self.confirm(token.token, "password123").status_code, 400)
        token.refresh_from_db()
        self.assertIsNone(token.used_at)
        self.assertEqual(self.confirm(token.token).status_code, 200)

    def test_confirm_invalidates_existing_sessions(self):
        old_client = Client(enforce_csrf_checks=True)
        csrf = old_client.get("/api/auth/session/").json()["csrfToken"]
        login = old_client.post(
            "/api/auth/login/",
            data=json.dumps({"email": "ana@example.test", "password": "old-password-123"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(old_client.get("/api/folders/").status_code, 200)

        self.request_reset()
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(self.confirm(token.token).status_code, 200)

        self.assertEqual(old_client.get("/api/folders/").status_code, 403)
        self.assertIsNone(old_client.get("/api/auth/session/").json()["user"])


class RegistrationAndVerificationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_preserves_password_spaces(self):
        password = "  Existing-P@ssword-493!  "
        get_user_model().objects.create_user(
            name="Space Login",
            email="space-login@example.test",
            password=password,
            account_status=get_user_model().AccountStatus.ACTIVE,
            email_verified=True,
        )

        response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"email": "space-login@example.test", "password": password}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

    def test_registration_creates_pending_client(self):
        data = {
            "name": "Carlos Gomez",
            "email": "carlos@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertEqual(res_data["email"], "carlos@example.test")
        self.assertEqual(res_data["name"], "Carlos Gomez")
        self.assertEqual(res_data["role"], "cliente")
        self.assertEqual(res_data["account_status"], "pendiente_verificacion")
        self.assertFalse(res_data["email_verified"])

        # Verificar en base de datos
        user = get_user_model().objects.get(email="carlos@example.test")
        self.assertEqual(user.role, get_user_model().Role.CLIENTE)
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_ignores_tampered_role_and_status(self):
        # Un atacante intenta enviarse como Administrador y Activo
        data = {
            "name": "Attacker",
            "email": "attacker@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
            "role": "administrador",
            "account_status": "activa",
            "email_verified": True,
            "is_staff": True,
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)

        user = get_user_model().objects.get(email="attacker@example.test")
        self.assertEqual(user.role, get_user_model().Role.CLIENTE)
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)
        self.assertFalse(user.email_verified)

    def test_registration_duplicate_email_rejected(self):
        get_user_model().objects.create_user(
            name="Existing", email="existing@example.test", password="Password123!"
        )
        data = {
            "name": "Duplicate",
            "email": "EXISTING@example.test",  # comprueba normalización a minúsculas
            "password": "Password123!",
            "password_confirmation": "Password123!",
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")
        self.assertIn("email", response.json()["field_errors"])

    def test_registration_password_mismatch(self):
        data = {
            "name": "Mismatch",
            "email": "mismatch@example.test",
            "password": "Password123!",
            "password_confirmation": "DifferentPass123!",
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirmation", response.json()["field_errors"])

    def test_registration_rejects_password_similar_to_email(self):
        data = {
            "name": "Ana Prueba",
            "email": "ana@example.test",
            "password": "ana@example.test",
            "password_confirmation": "ana@example.test",
        }

        response = self.client.post(
            "/api/auth/register/", data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["field_errors"])
        self.assertFalse(get_user_model().objects.filter(email=data["email"]).exists())

    def test_registration_rejects_password_with_only_spaces(self):
        data = {
            "name": "Space User",
            "email": "spaces@example.test",
            "password": "            ",
            "password_confirmation": "            ",
        }

        response = self.client.post(
            "/api/auth/register/", data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("solo espacios", str(response.json()["field_errors"]["password"]))

    def test_registration_preserves_leading_and_trailing_password_spaces(self):
        password = "  Strong-P@ssword-493!  "
        data = {
            "name": "Space User",
            "email": "spaces@example.test",
            "password": password,
            "password_confirmation": password,
        }

        response = self.client.post(
            "/api/auth/register/", data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(email=data["email"])
        self.assertTrue(user.check_password(password))

    def test_verify_email_success(self):
        from accounts import services
        user = get_user_model().objects.create_user(
            name="To Verify", email="toverify@example.test", password="Password123!"
        )
        token = services.generate_verification_token(user)

        response = self.client.post(
            "/api/auth/verify-email/",
            data=json.dumps({"token": token}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertEqual(user.account_status, get_user_model().AccountStatus.ACTIVE)
        self.assertTrue(user.email_verified)

    def test_verify_email_uses_configured_ttl(self):
        from accounts import services

        user = get_user_model().objects.create_user(
            name="TTL User", email="ttl@example.test", password="Password123!"
        )
        payload = f"{user.pk}:{user.updated_at.timestamp()}"
        with override_settings(EMAIL_VERIFICATION_TOKEN_TTL_MINUTES=45):
            with mock.patch(
                "accounts.services.TimestampSigner.unsign", return_value=payload
            ) as unsign:
                services.verify_email_with_token("signed-token")

        unsign.assert_called_once_with("signed-token", max_age=45 * 60)

    def test_verify_email_invalid_and_used_tokens(self):
        from accounts import services
        user = get_user_model().objects.create_user(
            name="To Verify", email="used@example.test", password="Password123!"
        )
        token = services.generate_verification_token(user)

        # Primer uso -> Exitoso
        res1 = self.client.post("/api/auth/verify-email/", data=json.dumps({"token": token}), content_type="application/json")
        self.assertEqual(res1.status_code, 200)

        # Segundo uso con el mismo token -> Rechazado por used_token
        res2 = self.client.post("/api/auth/verify-email/", data=json.dumps({"token": token}), content_type="application/json")
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.json()["code"], "used_token")

        # Token adulterado -> Rechazado por invalid_token
        res3 = self.client.post("/api/auth/verify-email/", data=json.dumps({"token": "tampered:token:value"}), content_type="application/json")
        self.assertEqual(res3.status_code, 400)
        self.assertEqual(res3.json()["code"], "invalid_token")

    def test_resend_verification_invalidates_previous_token(self):
        from accounts import services
        user = get_user_model().objects.create_user(
            name="Resend User", email="resend@example.test", password="Password123!"
        )
        token_antiguo = services.generate_verification_token(user)

        # Se adelanta el reloj para saltar el cooldown de 60 s
        future = timezone.now() + timedelta(seconds=61)
        with mock.patch("django.utils.timezone.now", return_value=future):
            res_resend = self.client.post(
                "/api/auth/resend-verification/",
                data=json.dumps({"email": "resend@example.test"}),
                content_type="application/json"
            )
        self.assertEqual(res_resend.status_code, 200)

        # El token antiguo ahora debe fallar
        res_old = self.client.post(
            "/api/auth/verify-email/",
            data=json.dumps({"token": token_antiguo}),
            content_type="application/json"
        )
        self.assertEqual(res_old.status_code, 400)
        self.assertEqual(res_old.json()["code"], "invalid_token")

    def test_pending_user_cannot_access_private_features(self):
        user = get_user_model().objects.create_user(
            name="Pending", email="pending@example.test", password="Password123!"
        )
        # La propiedad can_use_private_features debe ser falsa
        self.assertFalse(user.can_use_private_features)

        # Intentar iniciar sesión antes de verificar debe ser rechazado
        csrf_token = self.client.get("/api/auth/session/").json()["csrfToken"]
        res_login = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"email": "pending@example.test", "password": "Password123!"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(res_login.status_code, 401)

    def test_registration_delivers_real_email_and_sets_email_sent_true(self):
        mail.outbox.clear()
        data = {
            "name": "Lucia Real",
            "email": "lucia@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertTrue(res_data["email_sent"])

        # Verificar que Django mail puso el correo en el outbox
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["lucia@example.test"])
        self.assertIn("Verifica tu correo", sent_email.subject)
        self.assertIn("/verify-email?token=", sent_email.body)

    def test_registration_returns_503_but_keeps_pending_account_on_delivery_failure(self):
        mail.outbox.clear()
        data = {
            "name": "Failed Mail",
            "email": "failedmail@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
        }
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("Conexión rechazada")):
            response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "email_delivery_failed")

        user = get_user_model().objects.get(email="failedmail@example.test")
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_persists_valid_plan_preference(self):
        from subscriptions.models import Plan, PlanVersion, SubscriptionPreference
        plan = Plan.objects.create(code="pro", name="Pro", is_available=True)
        version = PlanVersion.objects.create(
            plan=plan, version_number=1, price=50, capacity_bytes=1073741824, duration_days=30
        )
        data = {
            "name": "User With Plan",
            "email": "withplan@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
            "preferred_plan_version_id": version.id,
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertTrue(res_data["preference_saved"])

        # Verificar en base de datos que se guardó en SubscriptionPreference
        user = get_user_model().objects.get(email="withplan@example.test")
        pref = SubscriptionPreference.objects.filter(user=user).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.plan_version_id, version.id)

    def test_registration_without_plan_preference_sets_preference_saved_false(self):
        from subscriptions.models import SubscriptionPreference
        data = {
            "name": "No Plan",
            "email": "noplan@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertFalse(res_data["preference_saved"])

        user = get_user_model().objects.get(email="noplan@example.test")
        self.assertFalse(SubscriptionPreference.objects.filter(user=user).exists())

    def test_registration_with_invalid_plan_preference_sets_preference_saved_false(self):
        from subscriptions.models import SubscriptionPreference
        data = {
            "name": "Invalid Plan",
            "email": "invalidplan@example.test",
            "password": "Password123!",
            "password_confirmation": "Password123!",
            "preferred_plan_version_id": 999999,
        }
        response = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertFalse(res_data["preference_saved"])

        # El usuario aún así fue creado de forma segura
        user = get_user_model().objects.get(email="invalidplan@example.test")
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)
        self.assertFalse(SubscriptionPreference.objects.filter(user=user).exists())

    def _resend(self, email):
        return self.client.post(
            "/api/auth/resend-verification/",
            data=json.dumps({"email": email}),
            content_type="application/json",
        )

    def test_resend_within_cooldown_returns_429(self):
        from accounts import services
        user = get_user_model().objects.create_user(
            name="Cool", email="cool@example.test", password="Password123!"
        )
        services.generate_verification_token(user)
        mail.outbox.clear()

        response = self._resend("cool@example.test")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "resend_cooldown")
        self.assertGreater(response.json()["retry_after"], 0)
        self.assertIn("Retry-After", response)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_after_cooldown_sends_email(self):
        from accounts import services
        user = get_user_model().objects.create_user(
            name="Later", email="later@example.test", password="Password123!"
        )
        services.generate_verification_token(user)
        mail.outbox.clear()

        future = timezone.now() + timedelta(seconds=61)
        with mock.patch("django.utils.timezone.now", return_value=future):
            response = self._resend("later@example.test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_reports_delivery_failure(self):
        from accounts import services
        user = get_user_model().objects.create_user(
            name="Fail", email="fail@example.test", password="Password123!"
        )
        services.generate_verification_token(user)

        future = timezone.now() + timedelta(seconds=61)
        with mock.patch("django.utils.timezone.now", return_value=future):
            with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
                response = self._resend("fail@example.test")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "email_delivery_failed")
        user.refresh_from_db()
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)

