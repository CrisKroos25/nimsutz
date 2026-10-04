import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings


@override_settings(SIMULATED_AUTH_ENABLED=True, SIMULATED_USER_ID=1)
class DemoSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            pk=1, username="test-demo", email="demo@example.test", password="test-password"
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
        self.assertEqual(self.client.get("/api/auth/session/").json()["user"]["id"], 1)
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
        get_user_model().objects.create_user(username="other", email="other@example.test", password="test-password")
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

    @override_settings(SIMULATED_AUTH_ENABLED=False)
    def test_demo_login_can_be_disabled(self):
        self.assertEqual(self.sign_in().status_code, 401)
