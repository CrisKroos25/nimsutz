"""La migración se detiene ante identidades duplicadas en lugar de borrar contratos."""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class IdentityMigrationGuardTests(TransactionTestCase):
    def test_duplicate_legacy_identities_abort_without_deleting_rows(self):
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes("subscriptions")
        user = get_user_model().objects.create_user(
            email="duplicate-migration@example.test", name="Duplicados"
        )
        second = None
        LegacySubscription = None
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("subscriptions", "0003_quote_execution_context")])
            apps = executor.loader.project_state(
                [("subscriptions", "0003_quote_execution_context")]
            ).apps
            LegacyPlan = apps.get_model("subscriptions", "Plan")
            LegacyVersion = apps.get_model("subscriptions", "PlanVersion")
            LegacySubscription = apps.get_model("subscriptions", "Subscription")
            plan = LegacyPlan.objects.create(code="legacy-duplicate", name="Anterior")
            version = LegacyVersion.objects.create(
                plan=plan,
                version_number=1,
                price="15.00",
                currency="GTQ",
                capacity_bytes=1073741824,
                duration_days=30,
            )
            values = {
                "user_id": user.pk,
                "plan_version": version,
                "status": "expired",
                "started_at": timezone.now() - timedelta(days=60),
                "expires_at": timezone.now() - timedelta(days=30),
            }
            first = LegacySubscription.objects.create(**values)
            second = LegacySubscription.objects.create(**values)
            with self.assertRaisesRegex(RuntimeError, "consolidación"):
                MigrationExecutor(connection).migrate(latest)
            self.assertEqual(
                LegacySubscription.objects.filter(user_id=user.pk).count(), 2
            )
            self.assertTrue(LegacySubscription.objects.filter(pk=first.pk).exists())
        finally:
            # Solo retirar el duplicado del fixture efímero para restaurar el esquema de las demás pruebas.
            if second is not None:
                LegacySubscription.objects.filter(pk=second.pk).delete()
            MigrationExecutor(connection).migrate(latest)
