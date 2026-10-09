# subscriptions/tests.py
from .errors import SubscriptionError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
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

    