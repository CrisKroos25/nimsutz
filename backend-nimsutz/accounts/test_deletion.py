from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from files.deletion import purge_account_objects
from files.models import File, Folder, PendingObjectDeletion, QuotaReservation
from files.storage.base import StorageError
from payments.models import CardMovement, Payment, PaymentDetail, TestCard
from subscriptions import services as subscriptions
from subscriptions.models import (
    CoveragePeriod,
    Quote,
    ScheduledChange,
    ScheduledOperation,
    Subscription,
    SubscriptionPreference,
)
from payments.services import execute_checkout
from django.contrib.auth.hashers import make_password

from .deletion import delete_own_account
from .models import PasswordResetToken
from .services import generate_verification_token


@override_settings(
    PAYMENTS_IDEMPOTENCY_SECRET="account-deletion-test-secret-at-least-32",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccountDeletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans", verbosity=0)
        User = get_user_model()
        cls.owner = User.objects.create_user(
            email="erase@example.test",
            name="Eliminar",
            password="OldPassword!8472",
            email_verified=True,
            account_status="activa",
        )
        cls.other = User.objects.create_user(
            email="keep@example.test",
            name="Conservar",
            password="OtherPassword!8472",
            email_verified=True,
            account_status="activa",
        )
        cls.card = TestCard.objects.create(
            number="9999000099990001",
            holder="QA DELETE",
            security_code_hash=make_password("123"),
            expiry_month=12,
            expiry_year=2030,
            balance="500.00",
        )
        basic = subscriptions.get_current_version("basic")
        for user in (cls.owner, cls.other):
            quote = subscriptions.prepare_quote(
                user=user, operation="contract", plan_version_id=basic.pk
            )
            execute_checkout(
                user=user,
                quote_id=quote.pk,
                operation_key=uuid4(),
                card_data={
                    "number": cls.card.number,
                    "holder": cls.card.holder,
                    "security_code": "123",
                    "expiry_month": 12,
                    "expiry_year": 2030,
                },
            )
        cls.subscription = Subscription.objects.get(user=cls.owner)
        # Referencias históricas protegidas entre intervalos de la misma cuenta.
        period = CoveragePeriod.objects.get(subscription=cls.subscription)
        CoveragePeriod.objects.create(
            subscription=cls.subscription,
            plan_version=basic,
            conditions=period.conditions,
            starts_at=period.starts_at,
            ends_at=period.ends_at,
            cycle_starts_at=period.starts_at,
            cycle_ends_at=period.ends_at,
            state="superseded",
            reason="test",
            supersedes=period,
            payment=period.payment,
        )
        free = subscriptions.get_current_version("free")
        scheduled = subscriptions.prepare_quote(
            user=cls.owner, operation="change", plan_version_id=free.pk
        )
        subscriptions.confirm_scheduled_quote(
            user=cls.owner, quote_id=scheduled.pk, operation_key=uuid4()
        )
        subscriptions.set_preference(user=cls.owner, plan_version_id=basic.pk)
        cls.reset = PasswordResetToken.issue(cls.owner)
        cls.verification_token = generate_verification_token(cls.owner)
        cls.folder = Folder.objects.create(owner=cls.owner, name="Privada")
        now = timezone.now()
        for state in ("available", "trashed", "uploading", "deleted"):
            file = File.objects.create(
                owner=cls.owner,
                folder=cls.folder,
                storage_key=f"{cls.owner.pk}/{uuid4().hex}",
                original_name=f"{state}.txt",
                content_type="text/plain",
                size_bytes=5,
                status=state,
            )
            File.objects.filter(pk=file.pk).update(created_at=now - timedelta(hours=1))
            QuotaReservation.objects.create(
                owner=cls.owner,
                file=file,
                reserved_bytes=5,
                status="pending" if state == "uploading" else "confirmed",
                expires_at=(
                    now + timedelta(minutes=5)
                    if state == "uploading"
                    else now - timedelta(minutes=10)
                ),
            )
        cls.owned_keys = set(
            File.objects.filter(owner=cls.owner).values_list("storage_key", flat=True)
        )
        cls.other_file = File.objects.create(
            owner=cls.other,
            storage_key=f"{cls.other.pk}/{uuid4().hex}",
            original_name="conservar.txt",
            content_type="text/plain",
            size_bytes=5,
            status="available",
        )
        LogEntry.objects.create(
            user=cls.other,
            content_type=ContentType.objects.get_for_model(Folder),
            object_id=str(cls.folder.pk),
            object_repr="Privada",
            action_flag=CHANGE,
        )

    def setUp(self):
        self.api = APIClient()
        self.api.force_login(self.owner)
        self.backend = Mock()
        self.objects = set(self.owned_keys) | {self.other_file.storage_key}
        self.backend.delete_object.side_effect = (
            lambda *, storage_key: self.objects.discard(storage_key)
        )
        patcher = patch("files.deletion.storage.get_backend", return_value=self.backend)
        patcher.start()
        self.addCleanup(patcher.stop)

    def delete(self, data=None):
        return self.api.delete(
            "/api/auth/account/",
            {"confirm": True} if data is None else data,
            format="json",
        )

    def test_removes_all_owned_data_and_invalidates_every_session(self):
        other_session = APIClient()
        other_session.force_login(self.owner)
        expired = APIClient()
        expired.force_login(self.owner)
        expired_key = expired.session.session_key
        Session.objects.filter(session_key=expired_key).update(
            expire_date=timezone.now() - timedelta(days=1)
        )
        keys = [
            self.api.session.session_key,
            other_session.session.session_key,
            expired_key,
        ]
        unrelated = APIClient()
        unrelated.force_login(self.other)
        unrelated_key = unrelated.session.session_key
        self.card.refresh_from_db()
        balance = self.card.balance
        own_payments = list(
            Payment.objects.filter(owner=self.owner).values_list("pk", flat=True)
        )
        response = self.delete()
        self.assertEqual(
            response.status_code, 202
        )  # Una URL de carga aún puede estar vigente.
        self.assertTrue(response.data["deletion_pending"])
        self.assertFalse(get_user_model().objects.filter(pk=self.owner.pk).exists())
        for model, filters in (
            (File, {"owner_id": self.owner.pk}),
            (Folder, {"owner_id": self.owner.pk}),
            (QuotaReservation, {"owner_id": self.owner.pk}),
            (Subscription, {"user_id": self.owner.pk}),
            (Quote, {"user_id": self.owner.pk}),
            (ScheduledOperation, {"owner_id": self.owner.pk}),
            (ScheduledChange, {"user_id": self.owner.pk}),
            (SubscriptionPreference, {"user_id": self.owner.pk}),
            (Payment, {"owner_id": self.owner.pk}),
            (PasswordResetToken, {"user_id": self.owner.pk}),
        ):
            self.assertFalse(model.objects.filter(**filters).exists(), model.__name__)
        self.assertFalse(
            CoveragePeriod.objects.filter(subscription_id=self.subscription.pk).exists()
        )
        self.assertFalse(
            PaymentDetail.objects.filter(payment_id__in=own_payments).exists()
        )
        self.assertFalse(
            CardMovement.objects.filter(payment_id__in=own_payments).exists()
        )
        self.assertFalse(Session.objects.filter(session_key__in=keys).exists())
        self.assertTrue(Session.objects.filter(session_key=unrelated_key).exists())
        self.assertFalse(LogEntry.objects.filter(object_repr="Privada").exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.assertTrue(File.objects.filter(pk=self.other_file.pk).exists())
        self.assertTrue(Payment.objects.filter(owner=self.other).exists())
        self.assertEqual(self.objects, {self.other_file.storage_key})
        self.card.refresh_from_db()
        self.assertEqual(self.card.balance, balance)
        self.assertIsNone(other_session.get("/api/auth/session/").data["user"])

    def test_same_email_registers_a_new_identity_with_no_previous_data(self):
        self.delete()
        response = self.api.post(
            "/api/auth/register/",
            {
                "name": "Nueva cuenta",
                "email": "ERASE@example.test",
                "password": "FreshAccess!84729",
                "password_confirmation": "FreshAccess!84729",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        new = get_user_model().objects.get(email=self.owner.email)
        self.assertNotEqual(new.pk, self.owner.pk)
        self.assertFalse(new.email_verified)
        self.assertEqual(new.account_status, "pendiente_verificacion")
        self.assertFalse(File.objects.filter(owner=new).exists())
        self.assertFalse(Payment.objects.filter(owner=new).exists())
        self.assertFalse(Subscription.objects.filter(user=new).exists())
        self.assertFalse(SubscriptionPreference.objects.filter(user=new).exists())
        old_reset = self.api.post(
            "/api/auth/password-reset/confirm/",
            {"token": self.reset.token, "new_password": "AnotherAccess!84729"},
            format="json",
        )
        self.assertNotEqual(old_reset.status_code, 200)
        old_verification = self.api.post(
            "/api/auth/verify-email/", {"token": self.verification_token}, format="json"
        )
        self.assertNotEqual(old_verification.status_code, 200)
        new.refresh_from_db()
        self.assertFalse(new.email_verified)

    def test_missing_or_ambiguous_confirmation_cannot_delete_anyone(self):
        for payload in (
            {},
            {"confirm": False},
            {"confirm": "true"},
            {"confirm": 1},
            {"confirm": True, "user_id": self.other.pk},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.delete(payload).status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.backend.delete_object.assert_not_called()

    def test_anonymous_and_missing_csrf_are_rejected(self):
        self.assertEqual(
            APIClient()
            .delete("/api/auth/account/", {"confirm": True}, format="json")
            .status_code,
            403,
        )
        secure = APIClient(enforce_csrf_checks=True)
        secure.force_login(self.owner)
        self.assertEqual(
            secure.delete(
                "/api/auth/account/", {"confirm": True}, format="json"
            ).status_code,
            403,
        )
        secure.get("/api/auth/session/")
        response = secure.delete(
            "/api/auth/account/",
            {"confirm": True},
            format="json",
            HTTP_X_CSRFTOKEN=secure.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 202)

    def test_database_failure_keeps_account_and_never_deletes_objects(self):
        with patch(
            "accounts.deletion.erase_customer_payments",
            side_effect=RuntimeError("database failure"),
        ):
            with self.assertRaises(RuntimeError):
                delete_own_account(self.owner)
        self.assertTrue(get_user_model().objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(Payment.objects.filter(owner=self.owner).exists())
        self.assertTrue(ScheduledOperation.objects.filter(owner=self.owner).exists())
        self.assertTrue(
            CoveragePeriod.objects.filter(subscription_id=self.subscription.pk).exists()
        )
        self.assertFalse(PendingObjectDeletion.objects.exists())
        self.backend.delete_object.assert_not_called()

    def test_storage_failure_queues_retry_without_retaining_the_account(self):
        self.backend.delete_object.side_effect = StorageError("offline")
        self.assertEqual(self.delete().status_code, 202)
        self.assertFalse(get_user_model().objects.filter(pk=self.owner.pk).exists())
        self.assertEqual(PendingObjectDeletion.objects.count(), len(self.owned_keys))
        self.backend.delete_object.side_effect = (
            lambda *, storage_key: self.objects.discard(storage_key)
        )
        with patch(
            "files.deletion.timezone.now",
            return_value=timezone.now() + timedelta(hours=1),
        ):
            call_command("cleanup_expired_uploads", stdout=StringIO())
        self.assertFalse(PendingObjectDeletion.objects.exists())
        self.assertEqual(self.objects, {self.other_file.storage_key})

    def test_late_upload_is_removed_after_its_previously_issued_url_expires(self):
        self.delete()
        task = PendingObjectDeletion.objects.get()
        self.objects.add(
            task.storage_key
        )  # PUT iniciado antes de la eliminación de cuenta.
        new_key = f"{self.other.pk}/new-object"
        self.objects.add(new_key)
        with patch(
            "files.deletion.timezone.now",
            return_value=task.finalize_after + timedelta(seconds=1),
        ):
            self.assertEqual(purge_account_objects(), 1)
        self.assertNotIn(task.storage_key, self.objects)
        self.assertIn(new_key, self.objects)
        self.assertFalse(PendingObjectDeletion.objects.exists())

    def test_empty_account_is_removed_immediately(self):
        empty = get_user_model().objects.create_user(
            email="empty@example.test",
            name="Vacía",
            email_verified=True,
            account_status="activa",
        )
        self.api.force_login(empty)
        response = self.delete()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["deletion_pending"])
        self.assertFalse(get_user_model().objects.filter(pk=empty.pk).exists())
        self.backend.delete_object.assert_not_called()


class ConcurrentAccountDeletionTests(TransactionTestCase):
    def test_two_confirmations_remove_the_same_account_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections

        User = get_user_model()
        owner = User.objects.create_user(
            email="parallel-delete@example.test",
            name="Eliminar",
            email_verified=True,
            account_status="activa",
        )
        other = User.objects.create_user(
            email="parallel-keep@example.test",
            name="Conservar",
            email_verified=True,
            account_status="activa",
        )
        barrier = Barrier(2)

        def remove():
            close_old_connections()
            try:
                user = User.objects.get(pk=owner.pk)
                barrier.wait(timeout=10)
                return delete_own_account(user)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(remove) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(results), [False, True])
        self.assertFalse(User.objects.filter(pk=owner.pk).exists())
        self.assertTrue(User.objects.filter(pk=other.pk).exists())
        self.assertFalse(PendingObjectDeletion.objects.exists())
