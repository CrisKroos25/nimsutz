"""Concurrencia comercial: identidad única, programación y vencimiento."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from . import services
from .errors import SubscriptionError
from .models import CoveragePeriod, ScheduledChange, ScheduledOperation, Subscription


@skipUnlessDBFeature("has_select_for_update")
class SubscriptionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        call_command("seed_plans", verbosity=0)
        self.user = get_user_model().objects.create_user(
            email="race-subscription@example.test",
            name="Concurrencia",
            email_verified=True,
            account_status="activa",
        )
        self.basic = services.get_current_version("basic")
        self.premium = services.get_current_version("premium")
        self.free = services.get_current_version("free")

    def parallel(self, actions):
        barrier = Barrier(len(actions))

        def run(action):
            try:
                barrier.wait(timeout=10)
                return action()
            except SubscriptionError as error:
                return error.code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as executor:
            return list(executor.map(run, actions))

    def test_simultaneous_selections_keep_single_identity(self):
        quotes = self.parallel(
            [
                lambda: services.prepare_quote(
                    user=self.user, operation="contract", plan_version_id=self.basic.pk
                ),
                lambda: services.prepare_quote(
                    user=self.user,
                    operation="contract",
                    plan_version_id=self.premium.pk,
                ),
            ]
        )
        self.assertEqual(len({quote.pk for quote in quotes}), 2)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Subscription.objects.get(user=self.user).status, "pending")
        self.assertFalse(CoveragePeriod.objects.exists())

    def test_simultaneous_confirmation_replays_same_result(self):
        # Contrato histórico válido: la confirmación no cobra ni extiende sus derechos.
        Subscription.objects.create(
            user=self.user,
            plan_version=self.premium,
            started_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=29),
        )
        quote = services.prepare_quote(
            user=self.user, operation="change", plan_version_id=self.free.pk
        )
        key = uuid4()
        action = lambda: services.confirm_scheduled_quote(
            user=self.user, quote_id=quote.pk, operation_key=key
        )
        results = self.parallel([action, action])
        self.assertEqual(results[0], results[1])
        self.assertEqual(ScheduledChange.objects.count(), 1)
        self.assertEqual(ScheduledOperation.objects.count(), 1)

    def test_simultaneous_expiry_creates_single_free_interval(self):
        Subscription.objects.create(
            user=self.user,
            plan_version=self.basic,
            started_at=timezone.now() - timedelta(days=31),
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        action = lambda: services.resolve_effective_subscription(self.user)
        results = self.parallel([action, action])
        self.assertEqual(results[0].pk, results[1].pk)
        self.assertTrue(all(sub.plan_version_id == self.free.pk for sub in results))
        self.assertEqual(
            CoveragePeriod.objects.filter(state="valid", ends_at__isnull=True).count(),
            1,
        )
