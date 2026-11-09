from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from files.models import File, QuotaReservation
from subscriptions.models import Plan, PlanVersion, Subscription
from .models import Payment, PaymentDetail


class AdministrationReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(email="admin@example.test", name="Admin", password="secret")
        cls.client_a = User.objects.create_user(email="one@example.test", name="Uno", email_verified=True,
                                                account_status="activa")
        cls.client_b = User.objects.create_user(email="two@example.test", name="Dos", email_verified=True,
                                                account_status="activa")
        plan = Plan.objects.create(code="qa", name="Plan QA")
        version = PlanVersion.objects.create(plan=plan, version_number=1, price=Decimal("12.00"), capacity_bytes=1000,
                                             duration_days=30)
        cls.subscription = Subscription.objects.create(user=cls.client_a, plan_version=version,
            status=Subscription.Status.ACTIVE, started_at=timezone.now(), expires_at=timezone.now())
        cls.payment = Payment.objects.create(owner=cls.client_a, operation_key="00000000-0000-0000-0000-000000000001",
            request_digest="a" * 64, quote_id="00000000-0000-0000-0000-000000000002", status="approved",
            operation="contract", amount=Decimal("12.00"), currency="GTQ", card_last4="1234",
            plan_snapshot={"plan_code": "qa", "version_id": version.pk, "name": "Plan QA", "capacity_bytes": 1000})
        PaymentDetail.objects.create(payment=cls.payment, code="cycle", description="Ciclo", amount="12.00")
        PaymentDetail.objects.create(payment=cls.payment, code="adjustment", description="Ajuste", amount="0.00")

    def setUp(self):
        self.api = APIClient()

    def test_metrics_count_trash_and_confirmed_bytes_but_not_reservations_or_deleted_files(self):
        available = File.objects.create(owner=self.client_a, storage_key="qa/available", original_name="a",
            content_type="text/plain", size_bytes=40, status=File.Status.AVAILABLE)
        trashed = File.objects.create(owner=self.client_a, storage_key="qa/trash", original_name="b",
            content_type="text/plain", size_bytes=30, status=File.Status.TRASHED)
        File.objects.create(owner=self.client_a, storage_key="qa/deleted", original_name="c",
            content_type="text/plain", size_bytes=90, status=File.Status.DELETED)
        QuotaReservation.objects.create(owner=self.client_a, file=available, reserved_bytes=40,
            status=QuotaReservation.Status.CONFIRMED, expires_at=timezone.now())
        QuotaReservation.objects.create(owner=self.client_a, file=trashed, reserved_bytes=30,
            status=QuotaReservation.Status.CONFIRMED, expires_at=timezone.now())
        QuotaReservation.objects.create(owner=self.client_a, file=None, reserved_bytes=90,
            status=QuotaReservation.Status.CONFIRMED, expires_at=timezone.now())
        QuotaReservation.objects.create(owner=self.client_a, reserved_bytes=500,
            status=QuotaReservation.Status.PENDING, expires_at=timezone.now())
        self.api.force_authenticate(self.admin)
        response = self.api.get("/api/administration/metrics/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["files"], {"total": 2, "in_trash": 1})
        self.assertEqual(response.data["storage"]["used_bytes"], 70)
        self.assertEqual(response.data["payments"]["approved_amount"], "12.00")
        self.assertEqual(response.data["active_subscriptions"], 0)
        self.assertEqual(File.objects.filter(owner=self.client_a).count(), 3)

    def test_effective_coverage_is_counted_and_expired_contract_is_not(self):
        from subscriptions.history import record_period
        now = timezone.now()
        starts_at = now - timezone.timedelta(days=1)
        self.subscription.started_at = starts_at
        self.subscription.expires_at = None
        self.subscription.save(update_fields=["started_at", "expires_at"])
        record_period(self.subscription, self.subscription.plan_version, starts_at, None, reason="test")
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.get("/api/administration/metrics/").data["active_subscriptions"], 1)
        self.subscription.coverage_history.update(ends_at=now, cycle_ends_at=now)
        self.assertEqual(self.api.get("/api/administration/metrics/").data["active_subscriptions"], 0)

    def test_payment_list_and_detail_are_cross_account_but_explicit_and_masked(self):
        self.api.force_authenticate(self.admin)
        response = self.api.get("/api/administration/payments/?client_id=%s" % self.client_a.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["client"]["email"], self.client_a.email)
        detail = self.api.get(f"/api/administration/payments/{self.payment.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["lines"]), 2)
        serialized = str(detail.data)
        for secret in ("request_digest", "operation_key", "quote_id", "result_snapshot", "balance", "number"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(detail.data["card_last4"], "1234")
        self.assertEqual(self.api.get(f"/api/payments/{self.payment.pk}/").status_code, 403)

    def test_personal_history_serializer_does_not_accept_admin_client_filter(self):
        from .read_serializers import AdministrationHistoryQuerySerializer, HistoryQuerySerializer
        personal = HistoryQuerySerializer(data={"client_id": str(self.client_a.pk)})
        self.assertFalse(personal.is_valid())
        admin = AdministrationHistoryQuerySerializer(data={"client_id": str(self.client_a.pk)})
        self.assertTrue(admin.is_valid(), admin.errors)

    def test_admin_payment_pagination_preserves_filters_and_orders_stably(self):
        for index in range(21):
            Payment.objects.create(owner=self.client_b,
                operation_key=f"10000000-0000-0000-0000-{index:012d}",
                request_digest="b" * 64, quote_id=f"20000000-0000-0000-0000-{index:012d}",
                status="rejected", operation="renew", amount="1.00", currency="GTQ",
                plan_snapshot={})
        self.api.force_authenticate(self.admin)
        response = self.api.get("/api/administration/payments/?status=rejected&operation=renew&page_size=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 21)
        self.assertIn("status=rejected", response.data["next"])
        self.assertIn("operation=renew", response.data["next"])
        self.assertIn("page=2", response.data["next"])
        self.assertEqual(len(response.data["results"]), 10)

    def test_client_and_unverified_or_suspended_admin_cannot_query(self):
        for user in (self.client_a,):
            self.api.force_authenticate(user)
            self.assertEqual(self.api.get("/api/administration/metrics/").status_code, 403)
            self.assertEqual(self.api.get("/api/administration/payments/").status_code, 403)
        for changes in ({"email_verified": False}, {"account_status": "suspendida"}):
            get_user_model().objects.filter(pk=self.admin.pk).update(**changes)
            self.admin.refresh_from_db()
            self.api.force_authenticate(self.admin)
            self.assertEqual(self.api.get("/api/administration/metrics/").status_code, 403)
            get_user_model().objects.filter(pk=self.admin.pk).update(email_verified=True, account_status="activa")

    def test_payment_period_uses_inclusive_guatemala_days(self):
        self.api.force_authenticate(self.admin)
        created = datetime(2026, 10, 1, 5, 59, 59, tzinfo=dt_timezone.utc)
        Payment.objects.filter(pk=self.payment.pk).update(created_at=created)
        response = self.api.get("/api/administration/metrics/?date_from=2026-09-30&date_to=2026-09-30")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["payments"]["approved_count"], 1)

    def test_query_validation_and_page_size_cap(self):
        from datetime import timedelta
        self.api.force_authenticate(self.admin)
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.assertEqual(self.api.get(f"/api/administration/metrics/?date_from={tomorrow.isoformat()}").status_code, 400)
        self.assertEqual(self.api.get("/api/administration/payments/?page_size=abc").status_code, 400)
