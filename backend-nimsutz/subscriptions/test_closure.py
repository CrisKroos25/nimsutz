"""Regresiones de R1–R9 con cobertura histórica y cobro real en PostgreSQL."""

from datetime import datetime, timedelta, timezone as utc
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from files.models import QuotaReservation
from payments.errors import PaymentError
from payments.models import Payment, TestCard
from payments.services import execute_checkout
from . import services
from .errors import SubscriptionError
from .models import (
    CoveragePeriod,
    Plan,
    PlanVersion,
    Quote,
    ScheduledChange,
    ScheduledOperation,
    Subscription,
)


@override_settings(
    PAYMENTS_IDEMPOTENCY_SECRET="subscription-closure-test-secret-32-characters",
    PAID_PLANS_ENABLED=True,
)
class SubscriptionClosureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans", verbosity=0)
        cls.basic = services.get_current_version("basic")
        cls.premium = services.get_current_version("premium")
        cls.free = services.get_current_version("free")
        cls.card = TestCard.objects.create(
            number="9999000000000001",
            holder="QA SUBSCRIPTIONS",
            security_code_hash=make_password("123"),
            expiry_month=12,
            expiry_year=2029,
            balance="500.00",
        )

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="closure@example.test",
            name="Cierre",
            email_verified=True,
            account_status="activa",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def quote(self, operation="contract", version=None):
        return services.prepare_quote(
            user=self.user,
            operation=operation,
            plan_version_id=(
                (version or self.basic).pk if operation != "renew" else None
            ),
        )

    def pay(self, quote, **changes):
        return execute_checkout(
            user=self.user,
            quote_id=quote.pk,
            operation_key=uuid4(),
            card_data={
                "number": self.card.number,
                "holder": self.card.holder,
                "expiry_month": 12,
                "expiry_year": 2029,
                "security_code": "123",
                **changes,
            },
        )

    def contract(self, version=None):
        self.pay(self.quote(version=version))
        return services.get_active_subscription(self.user)

    def confirm(self, quote, key=None):
        return services.confirm_scheduled_quote(
            user=self.user, quote_id=quote.pk, operation_key=key or uuid4()
        )

    def test_quote_creates_pending_identity_without_coverage(self):
        quote = self.quote()
        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.status, "pending")
        self.assertIsNone(sub.started_at)
        self.assertEqual(sub.selected_plan_version_id, self.basic.pk)
        self.assertIsNone(services.get_active_subscription(self.user))
        self.assertFalse(CoveragePeriod.objects.exists())
        response = self.client.get("/api/subscriptions/current/")
        self.assertIsNone(response.data["subscription"])
        self.assertEqual(response.data["pending_selection"]["subscription_id"], sub.pk)
        self.assertEqual(
            self.pay(quote, security_code="999")["payment"]["status"], "rejected"
        )
        sub.refresh_from_db()
        self.assertEqual(sub.status, "pending")
        self.assertEqual(sub.plan_version_id, self.basic.pk)

    def test_confirm_free_after_rejection_reuses_identity_and_creates_no_new_payment(
        self,
    ):
        self.pay(self.quote(), security_code="999")
        identity = Subscription.objects.get(user=self.user).pk
        sub, created = services.activate_free(
            user=self.user, plan_version_id=self.free.pk
        )
        self.assertTrue(created)
        self.assertEqual(sub.pk, identity)
        again, created = services.activate_free(
            user=self.user, plan_version_id=self.free.pk
        )
        self.assertFalse(created)
        self.assertEqual(again.pk, identity)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(CoveragePeriod.objects.filter(state="valid").count(), 1)

    def test_selection_changed_after_quote_requires_confirmation(self):
        old_quote = self.quote()
        self.quote(version=self.premium)
        with self.assertRaises(SubscriptionError) as error:
            self.pay(old_quote)
        self.assertEqual(error.exception.code, "plan_conditions_changed")
        self.assertFalse(Payment.objects.exists())

    def test_paid_coverage_cannot_be_applied_without_approval(self):
        quote = self.quote()
        with self.assertRaises(SubscriptionError) as error:
            services.apply_approved_quote(
                user=self.user, quote=services.quote_payload(quote), payment=None
            )
        self.assertEqual(error.exception.code, "forbidden")
        self.assertIsNone(services.get_active_subscription(self.user))

    def test_upgrade_preserves_originals_and_calendar_cycle(self):
        start = datetime(2028, 1, 31, 16, 30, tzinfo=utc.utc)
        with patch("django.utils.timezone.now", return_value=start):
            sub = self.contract()
            self.pay(self.quote("renew"))
        original = sub.coverage_history.get(reason="contract")
        original_end = original.ends_at
        at = datetime(2028, 2, 10, 16, 30, tzinfo=utc.utc)
        with patch("django.utils.timezone.now", return_value=at):
            self.pay(self.quote("change", self.premium))
            current = services.get_active_subscription(self.user)
        original.refresh_from_db()
        self.assertEqual(original.state, "superseded")
        self.assertEqual((original.starts_at, original.ends_at), (start, original_end))
        valid = list(sub.coverage_history.filter(state="valid").order_by("starts_at"))
        self.assertEqual(
            [p.conditions["plan_code"] for p in valid], ["basic", "premium", "premium"]
        )
        self.assertEqual(valid[0].ends_at, at)
        self.assertEqual(valid[1].starts_at, at)
        self.assertEqual(valid[1].cycle_starts_at, start)
        self.assertEqual(current.expires_at.day, 29)
        self.assertEqual(current.next_cycle_ends_at.day, 31)
        with patch("django.utils.timezone.now", return_value=current.expires_at):
            next_cycle = services.get_active_subscription(self.user)
        self.assertEqual(next_cycle.pk, sub.pk)
        self.assertEqual(next_cycle.cycle_anchor_day, 31)
        self.assertEqual(next_cycle.expires_at.day, 31)

    def test_late_reconciliation_never_grants_expired_prepaid_capacity(self):
        sub = self.contract()
        self.pay(self.quote("renew"))
        sub.refresh_from_db()
        paid_end = sub.coverage_end
        at = paid_end + timedelta(days=90)
        with patch("django.utils.timezone.now", return_value=at):
            first = services.get_active_subscription(self.user)
            second = services.get_active_subscription(self.user)
        self.assertEqual(first.pk, sub.pk)
        self.assertEqual(second.plan_version_id, self.free.pk)
        self.assertEqual(
            sub.coverage_history.filter(state="valid", ends_at__isnull=True).count(), 1
        )
        self.assertEqual(first.started_at, paid_end)
        self.assertEqual(Payment.objects.count(), 2)

    def test_names_and_prices_survive_catalog_publication(self):
        sub = self.contract()
        original_name = sub._effective_period.conditions["name"]
        Plan.objects.filter(pk=self.basic.plan_id).update(name="Básico nuevo")
        new_version = PlanVersion.objects.create(
            plan=Plan.objects.get(pk=self.basic.plan_id),
            version_number=2,
            price="20.00",
            currency="GTQ",
            capacity_bytes=2 * 1073741824,
            duration_days=30,
        )
        quote = self.quote("renew")
        self.assertEqual(quote.plan_snapshot["name"], original_name)
        self.assertEqual(quote.total, 15)
        self.pay(quote)
        current = services.subscription_payload(
            services.get_active_subscription(self.user)
        )
        self.assertEqual(current["plan"]["name"], original_name)
        self.assertEqual(new_version.name, "Básico nuevo")
        original = PlanVersion.objects.get(pk=self.basic.pk)
        original.price = "99.00"
        with self.assertRaises(ValidationError):
            original.save()

    def test_paid_downgrade_waits_for_manual_payment_after_expiry(self):
        sub = self.contract(self.premium)
        quote = self.quote("change", self.basic)
        result = self.confirm(quote)
        self.assertTrue(result["scheduled_change"]["requires_payment"])
        self.assertEqual(Payment.objects.count(), 1)
        with patch(
            "django.utils.timezone.now",
            return_value=sub.expires_at + timedelta(minutes=5),
        ):
            free = services.get_active_subscription(self.user)
            self.assertEqual(free.plan_version_id, self.free.pk)
            self.assertTrue(services.scheduled_change_payload(self.user)["payment_due"])
            self.assertEqual(Payment.objects.count(), 1)
            paid = self.pay(self.quote(version=self.basic))
            self.assertEqual(paid["payment"]["status"], "approved")
            self.assertEqual(paid["subscription"]["id"], sub.pk)
        self.assertEqual(
            Subscription.objects.get(user=self.user).plan_version_id, self.basic.pk
        )
        self.assertFalse(ScheduledChange.objects.filter(user=self.user).exists())

    def test_free_downgrade_allows_excess_without_erasing_usage(self):
        sub = self.contract(self.premium)
        reservation = QuotaReservation.objects.create(
            owner=self.user,
            reserved_bytes=150 * 1048576,
            status="confirmed",
            expires_at=timezone.now() + timedelta(days=60),
        )
        self.confirm(self.quote("change", self.free))
        with patch("django.utils.timezone.now", return_value=sub.expires_at):
            free = services.get_active_subscription(self.user)
        self.assertEqual(free.pk, sub.pk)
        self.assertEqual(free.plan_version_id, self.free.pk)
        self.assertTrue(
            QuotaReservation.objects.filter(
                pk=reservation.pk, status="confirmed"
            ).exists()
        )
        self.assertEqual(Payment.objects.count(), 1)

    def test_basic_capacity_is_rechecked_at_payment(self):
        sub = self.contract(self.premium)
        self.confirm(self.quote("change", self.basic))
        with patch(
            "django.utils.timezone.now",
            return_value=sub.expires_at + timedelta(minutes=1),
        ):
            quote = self.quote(version=self.basic)
            QuotaReservation.objects.create(
                owner=self.user,
                reserved_bytes=2 * 1073741824,
                status="confirmed",
                expires_at=timezone.now() + timedelta(days=1),
            )
            with self.assertRaises(SubscriptionError) as error:
                self.pay(quote)
            self.assertEqual(error.exception.code, "quota_exceeded")
        self.assertEqual(Payment.objects.count(), 1)

    def test_confirm_replay_ignores_expiry_and_never_resurrects_cancelled_change(self):
        self.contract(self.premium)
        quote = self.quote("change", self.free)
        key = uuid4()
        result = self.confirm(quote, key)
        services.cancel_scheduled_change(user=self.user)
        Quote.objects.filter(pk=quote.pk).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertEqual(self.confirm(quote, key), result)
        self.assertFalse(ScheduledChange.objects.exists())
        self.assertEqual(ScheduledOperation.objects.count(), 1)

    def test_same_confirmation_key_with_another_quote_conflicts(self):
        self.contract(self.premium)
        quote1 = self.quote("change", self.free)
        quote2 = self.quote("change", self.basic)
        key = uuid4()
        self.confirm(quote1, key)
        with self.assertRaises(SubscriptionError) as error:
            self.confirm(quote2, key)
        self.assertEqual(error.exception.code, "idempotency_conflict")

    def test_confirm_api_requires_uuid_and_empty_body(self):
        self.contract(self.premium)
        quote = self.quote("change", self.free)
        path = f"/api/subscriptions/quotes/{quote.pk}/confirm/"
        for body, key in [
            ({}, ""),
            ({"price": "0.00"}, str(uuid4())),
            ([], str(uuid4())),
        ]:
            response = self.client.post(
                path, body, format="json", HTTP_IDEMPOTENCY_KEY=key
            )
            self.assertEqual(response.status_code, 400, response.data)
        key = str(uuid4())
        first = self.client.post(path, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        second = self.client.post(path, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data, second.data)
        self.assertFalse(Payment.objects.filter(operation="change").exists())

    def test_schedule_revalidates_conditions(self):
        self.contract(self.premium)
        quote = self.quote("change", self.basic)
        self.pay(self.quote("renew"))
        with self.assertRaises(SubscriptionError) as error:
            self.confirm(quote)
        self.assertEqual(error.exception.code, "plan_conditions_changed")
        self.assertFalse(ScheduledChange.objects.exists())

    def test_unverified_customer_cannot_create_selection(self):
        get_user_model().objects.filter(pk=self.user.pk).update(email_verified=False)
        with self.assertRaises(SubscriptionError):
            self.quote()
        self.assertFalse(Subscription.objects.filter(user=self.user).exists())

    def test_reconciliation_worker_once_uses_effective_resolution_without_pii(self):
        start = timezone.now() - timedelta(days=31)
        Subscription.objects.create(
            user=self.user,
            plan_version=self.basic,
            started_at=start,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        output = StringIO()
        call_command("watch_subscriptions", once=True, stdout=output)
        self.assertEqual(
            Subscription.objects.get(user=self.user).plan_version_id, self.free.pk
        )
        self.assertNotIn(self.user.email, output.getvalue())

    def test_confirmation_requires_csrf_and_preserves_owner_isolation(self):
        self.contract(self.premium)
        quote = self.quote("change", self.free)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        path = f"/api/subscriptions/quotes/{quote.pk}/confirm/"
        response = client.post(
            path, {}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "csrf_failed")
        other = get_user_model().objects.create_user(
            email="other-closure@example.test",
            name="Otro",
            email_verified=True,
            account_status="activa",
        )
        self.client.force_authenticate(other)
        response = self.client.post(
            path, {}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ScheduledChange.objects.exists())

    def test_pending_or_admin_account_cannot_confirm_even_with_invalid_body(self):
        self.contract(self.premium)
        quote = self.quote("change", self.free)
        for fields in [
            {"email_verified": False},
            {"email_verified": True, "role": "administrador"},
        ]:
            get_user_model().objects.filter(pk=self.user.pk).update(**fields)
            self.user.refresh_from_db()
            self.client.force_authenticate(self.user)
            response = self.client.post(
                f"/api/subscriptions/quotes/{quote.pk}/confirm/",
                {"invalid": True},
                format="json",
            )
            self.assertEqual(response.status_code, 403, response.data)
            self.assertEqual(response.data["code"], "account_not_eligible")
        self.assertFalse(ScheduledChange.objects.exists())

    def test_worker_once_reports_database_failure(self):
        from django.core.management.base import CommandError
        from django.db import OperationalError

        with patch(
            "subscriptions.management.commands.watch_subscriptions.MigrationExecutor",
            side_effect=OperationalError,
        ), self.assertRaises(CommandError):
            call_command("watch_subscriptions", once=True)

    def test_worker_once_refuses_unapplied_migrations(self):
        from django.core.management.base import CommandError

        with patch(
            "subscriptions.management.commands.watch_subscriptions.MigrationExecutor"
        ) as executor:
            executor.return_value.migration_plan.return_value = [object()]
            with self.assertRaises(CommandError):
                call_command("watch_subscriptions", once=True)
