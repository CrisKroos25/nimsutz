from uuid import uuid4

from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class ClientRolePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="admin-role@example.test",
            name="Admin",
            password="test-password",
        )
        cls.client_user = User.objects.create_user(
            email="client-role@example.test",
            name="Client",
            password="test-password",
            role=User.Role.CLIENTE,
            account_status=User.AccountStatus.ACTIVE,
            email_verified=True,
        )

    def setUp(self):
        self.api = APIClient()

    def test_admin_is_forbidden_from_all_client_api_views(self):
        self.api.force_authenticate(self.admin)
        quote_id = uuid4()
        client_routes = [
            ("get", "/api/folders/"),
            ("post", "/api/folders/"),
            ("patch", "/api/folders/1/"),
            ("get", "/api/files/"),
            ("post", "/api/files/request-upload/"),
            ("post", "/api/files/1/confirm-upload/"),
            ("get", "/api/files/1/request-download/"),
            ("post", "/api/files/1/trash/"),
            ("post", "/api/files/1/restore/"),
            ("delete", "/api/files/1/permanent/"),
            ("get", "/api/files/upload-rules/"),
            ("get", "/api/subscriptions/preference/"),
            ("put", "/api/subscriptions/preference/"),
            ("get", "/api/subscriptions/current/"),
            ("post", "/api/subscriptions/activate-free/"),
            ("get", "/api/account/overview/"),
            ("post", "/api/subscriptions/quotes/"),
            ("get", f"/api/subscriptions/quotes/{quote_id}/"),
            ("post", f"/api/subscriptions/quotes/{quote_id}/confirm/"),
            ("delete", "/api/subscriptions/scheduled-change/"),
            ("post", "/api/payments/checkout/"),
            ("get", f"/api/payments/operations/{quote_id}/"),
            ("get", "/api/payments/results/1/"),
            ("get", "/api/payments/"),
            ("get", "/api/payments/1/"),
            ("delete", "/api/auth/account/"),
        ]

        for method, path in client_routes:
            with self.subTest(method=method, path=path):
                if method == "get":
                    response = self.api.get(path)
                elif method == "delete":
                    response = self.api.delete(path, data={"confirm": True}, format="json")
                else:
                    response = getattr(self.api, method)(path, data={}, format="json")
                self.assertEqual(response.status_code, 403)

    def test_active_verified_client_can_access_client_endpoints(self):
        self.api.force_authenticate(self.client_user)
        for path in (
            "/api/folders/",
            "/api/files/",
            "/api/subscriptions/current/",
            "/api/account/overview/",
            "/api/payments/",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.api.get(path).status_code, 200)
