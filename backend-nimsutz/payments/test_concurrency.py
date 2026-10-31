"""Pruebas de bloqueos reales: ejecutar con PostgreSQL, no con SQLite."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from subscriptions.services import activate_free

from .errors import PaymentError
from .models import CardMovement, Payment, TestCard
from .services import execute_checkout


@skipUnlessDBFeature('has_select_for_update')
@override_settings(PAYMENTS_IDEMPOTENCY_SECRET='concurrency-test-secret-32-characters')
class ConcurrentCheckoutTests(TransactionTestCase):
    def setUp(self):
        call_command('seed_plans', verbosity=0)
        self.user = get_user_model().objects.create_user(email='concurrent@example.test', name='Concurrente',
            email_verified=True, account_status='activa')
        self.card = TestCard.objects.create(number='9999000000000001', holder='NIM SUTZ DEMO',
            security_code_hash=make_password('123'), expiry_month=12,
            expiry_year=timezone.now().year + 2, balance='15.00')
        self.quote_id = uuid4()
        self.quote = {'id': str(self.quote_id), 'total': '15.00', 'currency': 'GTQ', 'operation': 'contract',
            'expires_at': (timezone.now() + timedelta(minutes=15)).isoformat(), 'requires_payment': True,
            'plan': {'name': 'Básico', 'version_id': 2},
            'lines': [{'code': 'contract_cycle', 'description': 'Primer ciclo', 'amount': '15.00'}]}
        self.card_data = {'number': self.card.number, 'holder': self.card.holder, 'expiry_month': 12,
            'expiry_year': self.card.expiry_year, 'security_code': '123'}

    def run_concurrent(self, users, keys):
        barrier = Barrier(2)
        def execute(args):
            user, key = args
            try:
                barrier.wait(timeout=10)
                return execute_checkout(user=user, quote_id=self.quote_id,
                    operation_key=key, card_data=self.card_data)
            except PaymentError as error:
                return error.code
            finally:
                connections.close_all()
        with patch('payments.commercial.validate_quote', return_value=self.quote), patch(
            'payments.commercial.apply_quote', side_effect=lambda **kw: activate_free(user=kw['user'])[0]
        ), ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(execute, zip(users, keys)))

    def test_simultaneous_same_key_debits_once(self):
        key = uuid4()
        results = self.run_concurrent([self.user, self.user], [key, key])
        self.assertEqual(sorted(result['replayed'] for result in results), [False, True])
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(CardMovement.objects.count(), 1)
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, 0)

    def test_simultaneous_new_keys_cannot_charge_same_quote_twice(self):
        results = self.run_concurrent([self.user, self.user], [uuid4(), uuid4()])
        self.assertIn('quote_already_processed', results)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(CardMovement.objects.count(), 1)

    def test_two_customers_cannot_overdraw_shared_test_card(self):
        other = get_user_model().objects.create_user(email='concurrent2@example.test', name='Otro',
            email_verified=True, account_status='activa')
        results = self.run_concurrent([self.user, other], [uuid4(), uuid4()])
        self.assertEqual(sorted(result['payment']['status'] for result in results), ['approved', 'rejected'])
        self.assertEqual(Payment.objects.get(status='rejected').reason_code, 'insufficient_funds')
        self.assertEqual(CardMovement.objects.count(), 1)
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, 0)
