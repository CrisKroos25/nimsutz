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


class CommercialSubscriptionCycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.user = make_user("commercial@example.test")
        cls.basic_v1 = services.get_current_version("basic")
        cls.premium_v1 = services.get_current_version("premium")
        cls.free_v1 = services.get_current_version("free")

    def test_calendar_months_and_anchor_recovery(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from subscriptions.calendar import add_calendar_months, calculate_cycle_interval

        tz = ZoneInfo("America/Guatemala")
        dt_jan31 = datetime(2026, 1, 31, 10, 0, tzinfo=tz)
        dt_feb = add_calendar_months(dt_jan31, 1, anchor_day=31)
        self.assertEqual(dt_feb.month, 2)
        self.assertEqual(dt_feb.day, 28)

        dt_mar = add_calendar_months(dt_jan31, 2, anchor_day=31)
        self.assertEqual(dt_mar.month, 3)
        self.assertEqual(dt_mar.day, 31)

        start, end = calculate_cycle_interval(dt_jan31)
        self.assertEqual(start.day, 31)
        self.assertEqual(end.day, 28)

    def test_double_renewal_and_single_cycle_advance_limit(self):
        # 1. Contratar inicial
        quote = services.prepare_quote(user=self.user, operation="contract", plan_version_id=self.basic_v1.pk)
        sub = services.apply_approved_quote(user=self.user, quote=services.quote_payload(quote), payment=None)
        self.assertEqual(sub.plan_version.plan.code, "basic")
        self.assertIsNone(sub.next_cycle_starts_at)

        # 2. Primera renovación: permitida
        quote_renew = services.prepare_quote(user=self.user, operation="renew")
        sub = services.apply_approved_quote(user=self.user, quote=services.quote_payload(quote_renew), payment=None)
        self.assertIsNotNone(sub.next_cycle_starts_at)
        self.assertEqual(sub.next_cycle_plan_version_id, self.basic_v1.pk)

        # 3. Segunda renovación: rechazada por límite de 1 ciclo anticipado
        with self.assertRaises(SubscriptionError) as ctx:
            services.prepare_quote(user=self.user, operation="renew")
        self.assertEqual(ctx.exception.code, "renewal_limit_reached")

    def test_upgrade_calculates_proration_and_future_cycle_difference(self):
        # 1. Contratar básico
        quote = services.prepare_quote(user=self.user, operation="contract", plan_version_id=self.basic_v1.pk)
        sub = services.apply_approved_quote(user=self.user, quote=services.quote_payload(quote), payment=None)

        # 2. Renovar un ciclo anticipado
        quote_renew = services.prepare_quote(user=self.user, operation="renew")
        services.apply_approved_quote(user=self.user, quote=services.quote_payload(quote_renew), payment=None)

        # 3. Cotizar upgrade a Premium (30.00 vs 15.00)
        upgrade_quote = services.prepare_quote(user=self.user, operation="change", plan_version_id=self.premium_v1.pk)
        self.assertEqual(len(upgrade_quote.lines), 2)
        # Línea 1: ajuste proporcional del ciclo actual
        self.assertEqual(upgrade_quote.lines[0]["code"], "current_cycle_adjustment")
        # Línea 2: diferencia completa del ciclo anticipado (30 - 15 = 15.00)
        self.assertEqual(upgrade_quote.lines[1]["code"], "next_cycle_adjustment")
        self.assertEqual(upgrade_quote.lines[1]["amount"], "15.00")

    def test_downgrade_schedule_and_quota_check(self):
        # Contratar premium
        quote = services.prepare_quote(user=self.user, operation="contract", plan_version_id=self.premium_v1.pk)
        sub = services.apply_approved_quote(user=self.user, quote=services.quote_payload(quote), payment=None)

        # Cotizar bajada a básico: requires_payment=False, kind=schedule_downgrade
        down_quote = services.prepare_quote(user=self.user, operation="change", plan_version_id=self.basic_v1.pk)
        self.assertFalse(down_quote.requires_payment)
        self.assertEqual(down_quote.effect["kind"], "schedule_downgrade")

        # Confirmar cambio programado
        scheduled, _ = services.confirm_scheduled_quote(user=self.user, quote_id=down_quote.id)
        self.assertEqual(scheduled.target_plan_version_id, self.basic_v1.pk)

        # Cancelar cambio programado
        services.cancel_scheduled_change(user=self.user)
        self.assertIsNone(services.scheduled_change_payload(self.user))

    def test_reconcile_command_transitions_expired_subscriptions(self):
        # Suscripción vencida sin ciclo anticipado -> vuelve a gratis
        quote = services.prepare_quote(user=self.user, operation="contract", plan_version_id=self.basic_v1.pk)
        sub = services.apply_approved_quote(user=self.user, quote=services.quote_payload(quote), payment=None)
        sub.expires_at = timezone.now() - timedelta(days=1)
        sub.save(update_fields=["expires_at"])

        # Correr comando de reconciliación
        call_command("reconcile_subscriptions")
        sub.refresh_from_db()
        self.assertEqual(sub.plan_version.plan.code, "free")
        self.assertIsNone(sub.expires_at)