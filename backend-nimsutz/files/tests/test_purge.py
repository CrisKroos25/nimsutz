# files/test_purge.py
import uuid
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from files import quota, services, storage_sync
from files.models import File, QuotaReservation
from files.storage.base import StorageError

BACKEND = "files.storage.get_backend"
DELETED = File.Status.DELETED


class PurgeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            name="Ana", email="ana@example.test", password="Password123!"
        )

    def make_file(self, name, status, *, purged=False):
        return File.objects.create(
            owner=self.user, folder=None,
            storage_key=f"{self.user.id}/{uuid.uuid4().hex}.pdf",
            original_name=name, content_type="application/pdf", size_bytes=1000,
            status=status, storage_purged_at=timezone.now() if purged else None,
        )

    def make_trashed(self, name="papelera.pdf"):
        file = self.make_file(name, File.Status.TRASHED)
        reservation = QuotaReservation.objects.create(
            owner=self.user, file=file, reserved_bytes=1000,
            status=QuotaReservation.Status.CONFIRMED, expires_at=timezone.now(),
        )
        return file, reservation

    def test_permanent_delete_frees_quota_and_marks_object_purged(self):
        file, reservation = self.make_trashed()
        self.assertEqual(quota.get_used_bytes(self.user), 1000)

        with mock.patch(BACKEND) as get_backend:
            services.permanently_delete_file(file=file, owner=self.user)
            get_backend.return_value.delete_object.assert_called_once_with(storage_key=file.storage_key)

        file.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(file.status, DELETED)
        self.assertEqual(reservation.status, QuotaReservation.Status.RELEASED)
        self.assertIsNotNone(file.storage_purged_at)
        self.assertEqual(quota.get_used_bytes(self.user), 0)

    def test_permanent_delete_succeeds_even_if_storage_is_down(self):
        file, _ = self.make_trashed()
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.delete_object.side_effect = StorageError("caido")
            with self.assertLogs("files", level="WARNING"):
                services.permanently_delete_file(file=file, owner=self.user)

        file.refresh_from_db()
        self.assertEqual(file.status, DELETED)
        self.assertIsNone(file.storage_purged_at)  # pendiente de reintento
        self.assertEqual(quota.get_used_bytes(self.user), 0)

    def test_purge_pending_retries_after_storage_recovers(self):
        file = self.make_file("a.pdf", DELETED)

        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.delete_object.side_effect = StorageError("caido")
            with self.assertLogs("files", level="WARNING"):
                self.assertEqual(storage_sync.purge_pending_objects(), (0, 1))
        file.refresh_from_db()
        self.assertIsNone(file.storage_purged_at)

        with mock.patch(BACKEND):
            self.assertEqual(storage_sync.purge_pending_objects(), (1, 0))
        file.refresh_from_db()
        self.assertIsNotNone(file.storage_purged_at)

    def test_purge_stops_after_three_consecutive_failures(self):
        for index in range(5):
            self.make_file(f"{index}.pdf", DELETED)

        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.delete_object.side_effect = StorageError("caido")
            with self.assertLogs("files", level="WARNING"):
                result = storage_sync.purge_pending_objects()
            self.assertEqual(get_backend.return_value.delete_object.call_count, 3)
        self.assertEqual(result, (0, 5))

    def test_purge_ignores_clean_and_non_deleted_files(self):
        self.make_file("limpio.pdf", DELETED, purged=True)
        self.make_file("viva.pdf", File.Status.AVAILABLE)

        with mock.patch(BACKEND) as get_backend:
            self.assertEqual(storage_sync.purge_pending_objects(), (0, 0))
            get_backend.return_value.delete_object.assert_not_called()