from copy import deepcopy
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from subscriptions.services import activate_free

from .errors import PaymentError
from .models import CardMovement, Payment, PaymentDetail, TestCard
from .serializers import CheckoutInputSerializer
from .services import execute_checkout, get_operation_result


@override_settings(PAYMENTS_IDEMPOTENCY_SECRET="test-only-secret-32-characters-long")
class CheckoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(email="pay@example.test", name="Pago",
            password="test-password", email_verified=True, account_status="activa")
        cls.card = TestCard.objects.create(number="9999000000000001", holder="NIM SUTZ DEMO",
            security_code_hash=make_password("123"), expiry_month=12,
            expiry_year=timezone.now().year + 2, balance="100.00")
        call_command("seed_plans", verbosity=0)

    def setUp(self):
        self.key = uuid4()
        self.quote = {"id": str(uuid4()), "total": "15.00", "currency": "GTQ", "operation": "contract",
            "expires_at": (timezone.now() + timedelta(minutes=15)).isoformat(), "requires_payment": True,
            "plan": {"plan_code": "basic", "version_id": 2, "name": "Básico"},
            "lines": [{"code": "contract_cycle", "description": "Primer ciclo", "amount": "15.00"}]}
        self.data = {"number": self.card.number, "holder": self.card.holder, "expiry_month": 12,
            "expiry_year": self.card.expiry_year, "security_code": "123"}
        # Dobles explícitos: no sustituyen las pruebas con la implementación comercial de Rodrigo.
        self.validate = patch("payments.commercial.validate_quote", return_value=self.quote).start()
        self.apply = patch("payments.commercial.apply_quote", side_effect=lambda **kw: activate_free(user=kw["user"])[0]).start()
        self.addCleanup(patch.stopall)

    def pay(self, **changes):
        from uuid import UUID
        args = {"user": self.user, "quote_id": UUID(self.quote["id"]),
                "operation_key": self.key, "card_data": self.data}
        args.update(changes)
        return execute_checkout(**args)

    def test_approval_and_replay_debit_once(self):
        first = self.pay()
        self.validate.side_effect = AssertionError("No revalidar una operación terminada")
        second = self.pay()
        self.assertEqual(first["payment"]["id"], second["payment"]["id"])
        self.assertTrue(second["replayed"])
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, Decimal("85.00"))
        self.assertEqual(CardMovement.objects.count(), 1)
        self.assertEqual(Payment.objects.get().lines.count(), 1)

    def test_changed_request_conflicts(self):
        self.pay()
        with self.assertRaises(PaymentError) as error:
            self.pay(card_data={**self.data, "security_code": "999"})
        self.assertEqual(error.exception.code, "idempotency_conflict")

    def test_same_quote_with_new_key_cannot_charge_twice(self):
        self.pay()
        with self.assertRaises(PaymentError) as error:
            self.pay(operation_key=uuid4())
        self.assertEqual(error.exception.code, "quote_already_processed")

    def test_technical_failure_rolls_back_everything(self):
        self.apply.side_effect = RuntimeError("commercial failure")
        with self.assertRaises(RuntimeError):
            self.pay()
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, Decimal("100.00"))
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(CardMovement.objects.exists())
        self.assertFalse(PaymentDetail.objects.exists())
        self.assertFalse(self.user.subscriptions.exists())

    def test_rejected_card_does_not_grant_coverage_or_debit(self):
        self.card.balance = 0
        self.card.save()
        result = self.pay()
        self.assertEqual(result["payment"]["reason_code"], "insufficient_funds")
        self.assertIsNone(result["subscription"])
        self.apply.assert_not_called()
        self.assertFalse(CardMovement.objects.exists())

    def test_rejection_can_be_corrected_with_new_key(self):
        self.pay(card_data={**self.data, "security_code": "999"})
        result = self.pay(operation_key=uuid4())
        self.assertEqual(result["payment"]["status"], "approved")
        self.assertEqual(Payment.objects.count(), 2)

    def test_all_card_rejection_reasons(self):
        cases = [({"enabled": False}, {}, "card_disabled"),
                 ({"expiry_year": 2001}, {"expiry_year": 2001}, "card_expired"),
                 ({"currency": "USD"}, {}, "currency_mismatch"),
                 ({}, {"holder": "OTRO"}, "card_details_invalid"),
                 ({}, {"number": "9999000000000099"}, "card_not_found")]
        for changes, inputs, reason in cases:
            with self.subTest(reason=reason):
                TestCard.objects.filter(pk=self.card.pk).update(enabled=True, currency="GTQ", expiry_year=self.data["expiry_year"])
                TestCard.objects.filter(pk=self.card.pk).update(**changes)
                result = self.pay(operation_key=uuid4(), card_data={**self.data, **inputs})
                self.assertEqual(result["payment"]["reason_code"], reason)
        self.assertFalse(CardMovement.objects.exists())

    def test_zero_adjustment_is_recorded(self):
        self.quote.update(total="0.00", operation="change")
        self.quote["lines"][0]["amount"] = "0.00"
        self.assertEqual(self.pay()["payment"]["amount"], "0.00")
        self.assertEqual(CardMovement.objects.get().amount, 0)

    def test_expired_quote_and_bad_total_do_not_charge(self):
        for change in [{"expires_at": (timezone.now()-timedelta(seconds=1)).isoformat()}, {"total": "9.00"}]:
            original = deepcopy(self.quote)
            self.quote.update(change)
            with self.assertRaises(PaymentError):
                self.pay()
            self.quote.clear(); self.quote.update(original)
        self.assertFalse(Payment.objects.exists())

    def test_unknown_operation_and_other_user_are_not_visible(self):
        self.pay()
        other = get_user_model().objects.create_user(email="other@example.test", name="Otro",
            email_verified=True, account_status="activa")
        with self.assertRaises(PaymentError) as error:
            get_operation_result(user=other, operation_key=self.key)
        self.assertEqual(error.exception.status, 404)

    def test_unverified_or_admin_cannot_pay(self):
        for fields in [{"email_verified": False}, {"role": "administrador"}]:
            get_user_model().objects.filter(pk=self.user.pk).update(email_verified=True, role="cliente", **{})
            get_user_model().objects.filter(pk=self.user.pk).update(**fields)
            with self.assertRaises(PaymentError) as error:
                self.pay()
            self.assertEqual(error.exception.status, 403)
        self.assertFalse(Payment.objects.exists())

    def test_api_invalid_input_and_csrf_do_not_create_payment(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post("/api/payments/checkout/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post("/api/payments/checkout/", {"quote_id": self.quote["id"], "card": {}},
                               format="json", HTTP_IDEMPOTENCY_KEY=str(self.key))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.exists())

    def test_secret_required(self):
        with override_settings(PAYMENTS_IDEMPOTENCY_SECRET=""):
            with self.assertRaises(PaymentError) as error:
                self.pay()
        self.assertEqual(error.exception.status, 503)

    def test_credential_values_are_not_persisted_in_payment(self):
        self.pay()
        payment = Payment.objects.get()
        self.assertEqual(len(payment.request_digest), 64)
        self.assertNotIn(self.data["number"], str(payment.result_snapshot))
        self.assertEqual(payment.card_last4, "0001")

    @override_settings(DEBUG=True)
    def test_seed_does_not_reset_existing_balance(self):
        self.pay()
        call_command("seed_payment_cards", verbosity=0)
        call_command("seed_payment_cards", verbosity=0)
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, Decimal("85.00"))
        self.assertEqual(TestCard.objects.count(), 5)

    def test_last_instant_of_expiry_month_is_valid_in_guatemala(self):
        TestCard.objects.filter(pk=self.card.pk).update(expiry_month=2, expiry_year=2028)
        self.data.update(expiry_month=2, expiry_year=2028)
        now = datetime(2028, 3, 1, 5, 59, 59, tzinfo=datetime_timezone.utc)
        self.quote['expires_at'] = (now + timedelta(minutes=15)).isoformat()
        with patch('payments.services.timezone.now', return_value=now):
            self.assertEqual(self.pay()['payment']['status'], 'approved')

    def test_rejection_preserves_existing_balance_and_subscription(self):
        subscription, _ = activate_free(user=self.user)
        result = self.pay(card_data={**self.data, 'security_code': '999'})
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, Decimal('100.00'))
        self.assertEqual(result['subscription']['id'], subscription.pk)
        self.assertEqual(Payment.objects.get().reason_code, 'card_details_invalid')
        self.assertEqual(PaymentDetail.objects.count(), 1)
        self.apply.assert_not_called()

    def test_api_success_and_recovery_share_result_without_credentials(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post('/api/payments/checkout/', {'quote_id': self.quote['id'], 'card': self.data},
                               format='json', HTTP_IDEMPOTENCY_KEY=str(self.key))
        self.assertEqual(response.status_code, 200)
        payment_id = response.data['payment']['id']
        for path in [f'/api/payments/operations/{self.key}/', f'/api/payments/results/{payment_id}/']:
            recovered = client.get(path)
            self.assertEqual(recovered.status_code, 200)
            self.assertEqual(recovered.data['payment'], response.data['payment'])
            self.assertNotIn('security_code', str(recovered.data))
            self.assertNotIn(self.data['number'], str(recovered.data))
        other = get_user_model().objects.create_user(email='private@example.test', name='Otro',
            email_verified=True, account_status='activa')
        client.force_authenticate(other)
        self.assertEqual(client.get(f'/api/payments/results/{payment_id}/').status_code, 404)

    def test_api_errors_have_uniform_contract_and_no_payment(self):
        client = APIClient()
        response = client.post('/api/payments/checkout/', {}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'forbidden')
        client.force_authenticate(self.user)
        payload = {'quote_id': self.quote['id'], 'card': self.data}
        for headers, extra in [({}, {}), ({'HTTP_IDEMPOTENCY_KEY': str(self.key)}, {'amount': '0.00'})]:
            response = client.post('/api/payments/checkout/', {**payload, **extra}, format='json', **headers)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data['code'], 'invalid_request')
        self.assertFalse(Payment.objects.exists())

    def test_api_technical_failure_is_not_a_card_rejection(self):
        self.apply.side_effect = RuntimeError('do not expose request')
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post('/api/payments/checkout/', {'quote_id': self.quote['id'], 'card': self.data},
                               format='json', HTTP_IDEMPOTENCY_KEY=str(self.key))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['code'], 'payment_service_unavailable')
        self.assertFalse(Payment.objects.exists())
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, Decimal('100.00'))

    def test_card_holder_normalization_and_unknown_fields(self):
        serializer = CheckoutInputSerializer(data={'quote_id': self.quote['id'],
            'card': {**self.data, 'holder': ' nim   sutz demo '}})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['card']['holder'], self.card.holder)
        serializer = CheckoutInputSerializer(data={'quote_id': self.quote['id'],
            'card': {**self.data, 'balance': '9999.00'}})
        self.assertFalse(serializer.is_valid())

    def test_failed_coverage_write_is_rolled_back(self):
        def fail_after_write(**kwargs):
            activate_free(user=kwargs['user'])
            raise RuntimeError('coverage write failed')
        self.apply.side_effect = fail_after_write
        with self.assertRaises(RuntimeError):
            self.pay()
        self.assertFalse(self.user.subscriptions.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(PaymentDetail.objects.exists())
        self.assertFalse(CardMovement.objects.exists())

    def test_seed_is_forbidden_outside_test_environment(self):
        from django.core.management.base import CommandError
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command('seed_payment_cards', verbosity=0)
