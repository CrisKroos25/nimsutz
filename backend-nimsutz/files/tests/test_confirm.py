# files/test_confirm.py
import uuid
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from files import quota, services, storage_sync
from files.models import File, QuotaReservation
from files.storage.base import StorageError

BACKEND = "files.storage.get_backend"
GOOD = {"ContentLength": 1000, "ContentType": "application/pdf"}


class ConfirmUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            name="Ana", email="ana@example.test", password="Password123!"
        )
        self.file = File.objects.create(
            owner=self.user, folder=None,
            storage_key=f"{self.user.id}/{uuid.uuid4().hex}.pdf",
            original_name="informe.pdf", content_type="application/pdf",
            size_bytes=1000, status=File.Status.UPLOADING,
        )
        self.reservation = QuotaReservation.objects.create(
            owner=self.user, file=self.file, reserved_bytes=1000,
            status=QuotaReservation.Status.PENDING,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def assert_discarded(self):
        self.file.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.file.status, File.Status.DELETED)
        self.assertEqual(self.reservation.status, QuotaReservation.Status.RELEASED)
        self.assertEqual(quota.get_used_bytes(self.user), 0)

    def test_valid_object_is_confirmed(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = GOOD
            services.confirm_upload(file=self.file, owner=self.user)

        self.file.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.file.status, File.Status.AVAILABLE)
        self.assertEqual(self.reservation.status, QuotaReservation.Status.CONFIRMED)
        self.assertEqual(quota.get_used_bytes(self.user), 1000)

    def test_wrong_size_is_discarded_and_object_deleted(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = {**GOOD, "ContentLength": 2000}
            with self.assertRaisesMessage(ValidationError, "tamaño real"):
                services.confirm_upload(file=self.file, owner=self.user)
            get_backend.return_value.delete_object.assert_called_once_with(
                storage_key=self.file.storage_key
            )
        self.assert_discarded()

    def test_wrong_content_type_is_discarded(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = {**GOOD, "ContentType": "text/html"}
            with self.assertRaisesMessage(ValidationError, "tipo del archivo"):
                services.confirm_upload(file=self.file, owner=self.user)
        self.assert_discarded()

    def test_missing_object_is_discarded(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = None
            with self.assertRaisesMessage(ValidationError, "no fue subido"):
                services.confirm_upload(file=self.file, owner=self.user)
        self.assert_discarded()

    def test_expired_reservation_is_rejected_even_with_valid_object(self):
        QuotaReservation.objects.filter(pk=self.reservation.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = GOOD
            with self.assertRaisesMessage(ValidationError, "venció"):
                services.confirm_upload(file=self.file, owner=self.user)
        self.assert_discarded()

    def test_storage_failure_changes_nothing(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.side_effect = StorageError("caido")
            with self.assertLogs("files", level="WARNING"):
                with self.assertRaises(services.StorageUnavailableError):
                    services.confirm_upload(file=self.file, owner=self.user)

        self.file.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.file.status, File.Status.UPLOADING)
        self.assertEqual(self.reservation.status, QuotaReservation.Status.PENDING)

    def test_confirming_twice_is_idempotent(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = GOOD
            services.confirm_upload(file=self.file, owner=self.user)
            fresh = File.objects.get(pk=self.file.pk)
            again = services.confirm_upload(file=fresh, owner=self.user)
            self.assertEqual(get_backend.return_value.head_object.call_count, 1)

        self.assertEqual(again.status, File.Status.AVAILABLE)

    def test_discard_survives_failure_deleting_the_object(self):
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.head_object.return_value = {**GOOD, "ContentLength": 2000}
            get_backend.return_value.delete_object.side_effect = StorageError("caido")
            with self.assertLogs("files", level="WARNING"):
                with self.assertRaises(ValidationError):
                    services.confirm_upload(file=self.file, owner=self.user)
        self.assert_discarded()

    def test_other_user_cannot_confirm(self):
        other = get_user_model().objects.create_user(
            name="Luis", email="luis@example.test", password="Password123!"
        )
        with mock.patch(BACKEND):
            with self.assertRaisesMessage(ValidationError, "no pertenece"):
                services.confirm_upload(file=self.file, owner=other)