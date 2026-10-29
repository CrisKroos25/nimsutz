"""Verifica una actualización conservando cuentas, propietarios y contratos anteriores."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from files.models import File, Folder
from subscriptions.models import Subscription


class ExistingDataMigrationTests(TransactionTestCase):
    def test_subscription_migrations_preserve_previous_data_and_contract(self):
        user = get_user_model().objects.create_user(email='migration@example.test', name='Migración')
        folder = Folder.objects.create(owner=user, name='Conservada')
        file = File.objects.create(owner=user, folder=folder, storage_key='migration-preserve-object',
            original_name='preservado.txt', content_type='text/plain', size_bytes=128, status='available')
        start = timezone.now()
        end = start + timedelta(days=28)
        latest = [('subscriptions', '0003_quote_execution_context')]
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([('subscriptions', '0001_initial')])
            apps = executor.loader.project_state([('subscriptions', '0001_initial')]).apps
            Plan = apps.get_model('subscriptions', 'Plan')
            Version = apps.get_model('subscriptions', 'PlanVersion')
            OldSubscription = apps.get_model('subscriptions', 'Subscription')
            plan = Plan.objects.create(code='migration-basic', name='Contrato histórico')
            version = Version.objects.create(plan=plan, version_number=1, price='15.00', currency='GTQ',
                capacity_bytes=1073741824, duration_days=30)
            subscription = OldSubscription.objects.create(user_id=user.pk, plan_version=version,
                status='active', started_at=start, expires_at=end)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            current = Subscription.objects.get(pk=subscription.pk)
            self.assertEqual(current.user_id, user.pk)
            self.assertEqual(current.plan_version_id, version.pk)
            self.assertEqual(current.plan_version.plan.name, 'Contrato histórico')
            self.assertEqual(current.started_at, start)
            self.assertEqual(current.expires_at, end)
            self.assertEqual(current.plan_version.price, 15)
            file.refresh_from_db()
            self.assertEqual((file.owner_id, file.folder_id, file.storage_key, file.size_bytes),
                (user.pk, folder.pk, 'migration-preserve-object', 128))
            self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
