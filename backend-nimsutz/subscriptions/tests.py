from datetime import timedelta
from django.contrib.auth import get_user_model
# subscriptions/tests.py
from .errors import SubscriptionError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from accounts.models import User
from . import services
from .models import Plan, Subscription
from django.test import TestCase


def make_user(email, **extra):
    return User.objects.create_user(
        email=email, name=email, password="test-password",
        account_status=User.AccountStatus.ACTIVE, email_verified=True, **extra,
    )


class FreeActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.user = make_user("a@example.test")

    def test_seed_is_idempotent(self):
        call_command("seed_plans")
        self.assertEqual(Plan.objects.count(), 3)

    def test_activate_free_grants_100mb_without_expiry(self):
        sub, created = services.activate_free(user=self.user)
        self.assertTrue(created)
        self.assertEqual(sub.plan_version.capacity_bytes, 100 * 1024 * 1024)
        self.assertIsNone(sub.expires_at)

    def test_activate_free_twice_does_not_duplicate(self):
        services.activate_free(user=self.user)
        _, created = services.activate_free(user=self.user)
        self.assertFalse(created)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)

    def test_pending_account_cannot_activate(self):
        pending = User.objects.create_user(email="p@example.test", name="P", password="test-password")
        with self.assertRaises(SubscriptionError):
            services.activate_free(user=pending)

    def test_database_rejects_second_active_subscription(self):
        sub, _ = services.activate_free(user=self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subscription.objects.create(
                user=self.user, plan_version=sub.plan_version, started_at=timezone.now()
            )

    def test_users_are_isolated(self):
        other = make_user("b@example.test")
        services.activate_free(user=self.user)
        self.assertIsNone(services.get_active_subscription(other))

    def test_preference_does_not_grant_coverage(self):
        premium = services.get_current_version("premium")
        services.set_preference(user=self.user, plan_version_id=premium.pk)
        self.assertIsNone(services.get_active_subscription(self.user))

    def test_unavailable_plan_rejected_as_preference(self):
        Plan.objects.filter(code="premium").update(is_available=False)
        premium_version = Plan.objects.get(code="premium").versions.first()
        with self.assertRaises(SubscriptionError):
            services.set_preference(user=self.user, plan_version_id=premium_version.pk)



class FreeActivationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.user = make_user("confirmation@example.test")
        cls.version = services.get_current_version("free")

    def setUp(self):
        self.client.force_login(self.user)

    def activate(self, payload):
        return self.client.post(
            "/api/subscriptions/activate-free/", payload, content_type="application/json"
        )

    def publish_version(self, **changes):
        return self.version.plan.versions.create(
            version_number=2, price=changes.get("price", 0),
            capacity_bytes=200 * 1024 * 1024, currency="GTQ", duration_days=None,
        )

    def test_version_required_and_positive(self):
        for payload in [{}, {"plan_version_id": None}, {"plan_version_id": 0},
                        {"plan_version_id": "invalid"}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.activate(payload).status_code, 400)
        self.assertFalse(Subscription.objects.exists())

    def test_confirmed_version_is_activated_idempotently(self):
        payload = {"plan_version_id": self.version.pk}
        first = self.activate(payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["subscription"]["plan"]["version_id"], self.version.pk)
        self.publish_version()
        second = self.activate(payload)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["subscription"]["id"], second.json()["subscription"]["id"])
        self.assertEqual(Subscription.objects.count(), 1)

    def test_stale_version_does_not_activate_new_conditions(self):
        self.publish_version()
        response = self.activate({"plan_version_id": self.version.pk})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "plan_conditions_changed")
        self.assertFalse(Subscription.objects.exists())

    def test_paid_or_unknown_version_cannot_activate_free(self):
        for version_id in [services.get_current_version("premium").pk, 999999]:
            with self.subTest(version_id=version_id):
                self.assertEqual(self.activate({"plan_version_id": version_id}).status_code, 409)
        self.assertFalse(Subscription.objects.exists())

    def test_unavailable_free_plan_cannot_activate(self):
        Plan.objects.filter(pk=self.version.plan_id).update(is_available=False)
        self.assertEqual(self.activate({"plan_version_id": self.version.pk}).status_code, 409)
        self.assertFalse(Subscription.objects.exists())

    def test_nonzero_price_cannot_be_activated_without_payment(self):
        version = self.publish_version(price=10)
        self.assertEqual(self.activate({"plan_version_id": version.pk}).status_code, 409)
        self.assertFalse(Subscription.objects.exists())

    def test_existing_subscription_is_not_replaced_by_new_version(self):
        self.activate({"plan_version_id": self.version.pk})
        version = self.publish_version()
        self.assertEqual(self.activate({"plan_version_id": version.pk}).status_code, 409)
        self.assertEqual(Subscription.objects.get(user=self.user).plan_version_id, self.version.pk)

class SessionDestinationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command("seed_plans")
        User = get_user_model()
        cls.user = User.objects.create_user(
            name="Destino", email="destination@example.test", password="test-password",
            account_status=User.AccountStatus.ACTIVE, email_verified=True,
        )

    def assert_destination(self, expected):
        client = Client(enforce_csrf_checks=True)
        anonymous = client.get("/api/auth/session/").json()
        self.assertIsNone(anonymous["destination"])
        login = client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": "test-password"},
            content_type="application/json", HTTP_X_CSRFTOKEN=anonymous["csrfToken"],
        )
        self.assertEqual(login.status_code, 200)
        for payload in [login.json(), client.get("/api/auth/session/").json()]:
            self.assertEqual(payload["destination"], expected)
            self.assertEqual(payload["user"]["id"], self.user.pk)
            self.assertTrue(payload["csrfToken"])

    def test_without_subscription_goes_to_plans(self):
        self.assert_destination("plans")

    def test_preference_goes_to_summary(self):
        from subscriptions import services
        services.set_preference(
            user=self.user, plan_version_id=services.get_current_version("premium").pk
        )
        self.assert_destination("plan_summary")

    def test_active_subscription_goes_to_files(self):
        from subscriptions import services
        services.activate_free(user=self.user)
        self.assert_destination("files")

    def test_expired_subscription_goes_to_plans(self):
        from subscriptions import services
        subscription, _ = services.activate_free(user=self.user)
        subscription.expires_at = timezone.now() - timedelta(seconds=1)
        subscription.save(update_fields=["expires_at"])
        self.assert_destination("plans")

    def test_administrator_goes_to_admin(self):
        self.user.role = self.user.Role.ADMINISTRADOR
        self.user.save(update_fields=["role"])
        self.assert_destination("admin")
