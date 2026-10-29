"""Checkout contra cotizaciones y cobertura reales, sin sustituir el motor comercial."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from subscriptions import services as commercial
from subscriptions.models import Plan, PlanVersion, Quote, ScheduledChange, Subscription
from .models import CardMovement, Payment, PaymentDetail, TestCard


@override_settings(PAID_PLANS_ENABLED=True, PAYMENTS_IDEMPOTENCY_SECRET='integration-only-secret-at-least-32-characters', DEBUG=True)
class RealCheckoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_plans', verbosity=0)
        call_command('seed_payment_cards', verbosity=0)
        cls.basic = PlanVersion.objects.get(plan__code='basic')
        cls.premium = PlanVersion.objects.get(plan__code='premium')

    def setUp(self):
        self.user = get_user_model().objects.create_user(email='integration@example.test', name='Integración',
            password='Integration-pass-2026', email_verified=True, account_status='activa')
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        session = self.client.get('/api/auth/session/').json()
        self.client.credentials(HTTP_X_CSRFTOKEN=session['csrfToken'])

    def quote(self, operation='contract', version=None):
        body = {'operation': operation}
        if version is not None:
            body['plan_version_id'] = version.pk
        elif operation == 'contract':
            body['plan_version_id'] = self.basic.pk
        response = self.client.post('/api/subscriptions/quotes/', body, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['quote']

    def pay(self, quote, number='9999000000000001', key=None, **changes):
        card = TestCard.objects.get(number=number)
        data = {'number': number, 'holder': card.holder, 'expiry_month': card.expiry_month,
                'expiry_year': card.expiry_year, 'security_code': '123', **changes}
        return self.client.post('/api/payments/checkout/', {'quote_id': quote['id'], 'card': data},
            format='json', HTTP_IDEMPOTENCY_KEY=str(key or uuid4()))

    def contract(self):
        response = self.pay(self.quote())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['payment']['status'], 'approved')
        return Subscription.objects.get(user=self.user)

    def test_contract_and_recovery_with_real_session_csrf(self):
        quote = self.quote()
        self.assertEqual(self.client.get(f"/api/subscriptions/quotes/{quote['id']}/").status_code, 200)
        key = uuid4()
        first = self.pay(quote, key=key)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data['payment']['status'], 'approved')
        self.assertEqual(first.data['destination'], 'files')
        second = self.pay(quote, key=key)
        self.assertTrue(second.data['replayed'])
        self.assertEqual(second.data['payment'], first.data['payment'])
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(CardMovement.objects.count(), 1)
        self.assertEqual(Quote.objects.get(pk=quote['id']).status, 'executed')
        recovered = self.client.get(f'/api/payments/operations/{key}/')
        self.assertEqual(recovered.data['payment'], first.data['payment'])
        self.assertEqual(self.client.get('/api/account/overview/').data['destination'], 'files')
        self.assertEqual(TestCard.objects.get(number='9999000000000001').balance, Decimal('485.00'))
        conflict = self.pay(quote, key=key, security_code='999')
        self.assertEqual(conflict.data['code'], 'idempotency_conflict')
        duplicate = self.pay(quote)
        self.assertEqual(duplicate.data['code'], 'quote_already_processed')

    def test_real_renewal_and_two_line_upgrade_preserve_identity(self):
        sub = self.contract()
        old_end = sub.expires_at
        renewal = self.pay(self.quote('renew'))
        self.assertEqual(renewal.status_code, 200, renewal.data)
        self.assertEqual(renewal.data['payment']['status'], 'approved')
        sub.refresh_from_db()
        future_end = sub.coverage_end
        upgrade = self.quote('change', self.premium)
        self.assertEqual([line['code'] for line in upgrade['lines']], ['current_cycle_adjustment', 'next_cycle_adjustment'])
        response = self.pay(upgrade)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['payment']['status'], 'approved')
        sub.refresh_from_db()
        self.assertEqual(sub.plan_version_id, self.premium.pk)
        self.assertEqual(sub.next_cycle_plan_version_id, self.premium.pk)
        self.assertEqual(sub.expires_at, old_end)
        self.assertEqual(sub.coverage_end, future_end)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        self.assertEqual(PaymentDetail.objects.filter(payment_id=response.data['payment']['id']).count(), 2)

    def test_rejections_keep_selection_balance_and_coverage(self):
        quote = self.quote()
        for number, reason in [('9999000000000002','insufficient_funds'), ('9999000000000003','card_disabled'),
                               ('9999000000000004','card_expired'), ('9999000000000005','currency_mismatch')]:
            with self.subTest(reason=reason):
                before = TestCard.objects.get(number=number).balance
                response = self.pay(quote, number=number)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data['payment']['reason_code'], reason)
                self.assertEqual(TestCard.objects.get(number=number).balance, before)
                self.assertFalse(Subscription.objects.filter(user=self.user, status='active').exists())
        self.assertEqual(Quote.objects.get(pk=quote['id']).status, 'pending')
        self.assertFalse(CardMovement.objects.exists())
        self.assertEqual(self.pay(quote).data['payment']['status'], 'approved')

    def test_failure_after_real_coverage_write_rolls_everything_back(self):
        quote = self.quote()
        key = uuid4()
        real_apply = commercial.apply_approved_quote
        def fail(**kwargs):
            real_apply(**kwargs)
            raise RuntimeError('injected after real coverage write')
        with patch('subscriptions.services.apply_approved_quote', side_effect=fail):
            response = self.pay(quote, key=key)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(PaymentDetail.objects.exists())
        self.assertFalse(CardMovement.objects.exists())
        self.assertFalse(Subscription.objects.filter(user=self.user).exists())
        self.assertEqual(Quote.objects.get(pk=quote['id']).status, 'pending')
        self.assertEqual(TestCard.objects.get(number='9999000000000001').balance, Decimal('500.00'))
        self.assertEqual(self.pay(quote, key=key).data['payment']['status'], 'approved')

    def test_completed_operation_replays_even_after_quote_expiry(self):
        quote = self.quote()
        key = uuid4()
        first = self.pay(quote, key=key)
        Quote.objects.filter(pk=quote['id']).update(expires_at=timezone.now() - timedelta(seconds=1))
        result = self.pay(quote, key=key)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(result.data['replayed'])
        self.assertEqual(result.data['payment'], first.data['payment'])

    def test_old_quote_without_execution_context_requires_confirmation(self):
        quote = self.quote()
        Quote.objects.filter(pk=quote['id']).update(execution_context={})
        result = self.pay(quote)
        self.assertEqual(result.status_code, 409, result.data)
        self.assertEqual(result.data['code'], 'plan_conditions_changed')
        self.assertFalse(Payment.objects.exists())

    def test_expired_unprocessed_quote_does_not_charge(self):
        quote = self.quote()
        Quote.objects.filter(pk=quote['id']).update(expires_at=timezone.now() - timedelta(seconds=1))
        result = self.pay(quote)
        self.assertEqual(result.status_code, 409, result.data)
        self.assertEqual(result.data['code'], 'quote_expired')
        self.assertFalse(Payment.objects.exists())

    def test_renewal_displays_and_persists_scheduled_change_extension(self):
        sub = self.contract()
        change = ScheduledChange.objects.create(user=self.user, subscription=sub,
            target_plan_version=PlanVersion.objects.get(plan__code='free'), effective_at=sub.expires_at)
        quote = self.quote('renew')
        self.assertEqual(quote['effect']['scheduled_change_at'], quote['effect']['ends_at'])
        response = self.pay(quote)
        self.assertEqual(response.status_code, 200, response.data)
        change.refresh_from_db()
        sub.refresh_from_db()
        self.assertEqual(change.effective_at, sub.coverage_end)

    def test_zero_adjustment_uses_simulator_and_records_movement(self):
        sub = self.contract()
        near_end = sub.expires_at - timedelta(seconds=1)
        self.client.force_authenticate(self.user)
        with patch('django.utils.timezone.now', return_value=near_end):
            quote = self.quote('change', self.premium)
            self.assertEqual(quote['total'], '0.00')
            result = self.pay(quote)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['payment']['status'], 'approved')
        self.assertEqual(CardMovement.objects.get(payment_id=result.data['payment']['id']).amount, Decimal('0.00'))

    def test_changed_catalog_rejects_before_debit(self):
        quote = self.quote()
        PlanVersion.objects.create(plan=self.basic.plan, version_number=2, price='16.00',
            currency='GTQ', capacity_bytes=self.basic.capacity_bytes, duration_days=30)
        response = self.pay(quote)
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data['code'], 'plan_conditions_changed')
        self.assertFalse(Payment.objects.exists())

    def test_inactive_plan_still_allows_existing_contract_renewal(self):
        self.contract()
        Plan.objects.filter(pk=self.basic.plan_id).update(is_available=False)
        result = self.pay(self.quote('renew'))
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['payment']['status'], 'approved')

    def test_renewal_after_upgrade_quote_requires_new_confirmation(self):
        self.contract()
        quote = self.quote('change', self.premium)
        self.assertEqual(self.pay(self.quote('renew')).status_code, 200)
        result = self.pay(quote)
        self.assertEqual(result.status_code, 409, result.data)
        self.assertEqual(result.data['code'], 'plan_conditions_changed')
        self.assertEqual(Payment.objects.count(), 2)

    def test_prepaid_cycle_is_effective_at_exact_boundary(self):
        sub = self.contract()
        self.assertEqual(self.pay(self.quote('renew')).status_code, 200)
        self.client.force_authenticate(self.user)
        with patch('django.utils.timezone.now', return_value=sub.expires_at):
            result = self.client.get('/api/subscriptions/current/')
        self.assertEqual(result.data['subscription']['plan']['plan_code'], 'basic')
        self.assertEqual(result.data['subscription']['id'], sub.pk)

    def test_quote_and_results_are_private_to_customer(self):
        quote = self.quote()
        payment = self.pay(quote).data['payment']
        other = get_user_model().objects.create_user(email='integration2@example.test', name='Otro',
            email_verified=True, account_status='activa')
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/api/subscriptions/quotes/{quote['id']}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/payments/results/{payment['id']}/").status_code, 404)
        history = self.client.get('/api/payments/')
        self.assertEqual(history.data['count'], 0)
