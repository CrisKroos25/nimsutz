# accounts/tests.py
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings


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


class RegistrationAndVerificationTests(TestCase):
    def setUp(self):
        self.client = Client()

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

        # Reenviar correo genera nuevo token e invalida el anterior
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