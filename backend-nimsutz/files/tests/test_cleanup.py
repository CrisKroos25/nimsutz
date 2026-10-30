# files/test_cleanup.py
import uuid
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from files import quota, services, storage_sync
from files.models import File, QuotaReservation
from files.storage.base import StorageError

PENDING = QuotaReservation.Status.PENDING
CONFIRMED = QuotaReservation.Status.CONFIRMED
RELEASED = QuotaReservation.Status.RELEASED
BACKEND = "files.storage.get_backend"


class ExpiredReservationCleanupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            name="Ana", email="ana@example.test", password="Password123!"
        )

    def make_upload(self, name, *, minutes_left, status=PENDING, size=1000):
        file = File.objects.create(
            owner=self.user, folder=None,
            storage_key=f"{self.user.id}/{uuid.uuid4().hex}.pdf",
            original_name=name, content_type="application/pdf", size_bytes=size,
            status=File.Status.UPLOADING if status == PENDING else File.Status.AVAILABLE,
        )
        reservation = QuotaReservation.objects.create(
            owner=self.user, file=file, reserved_bytes=size, status=status,
            expires_at=timezone.now() + timedelta(minutes=minutes_left),
        )
        return file, reservation

    def test_expired_pending_reservation_stops_counting_before_cleanup(self):
        self.make_upload("vencida.pdf", minutes_left=-1, size=1000)
        self.make_upload("vigente.pdf", minutes_left=10, size=500)
        self.assertEqual(quota.get_used_bytes(self.user), 500)

    def test_cleanup_releases_reservation_and_marks_file_deleted(self):
        file, reservation = self.make_upload("vencida.pdf", minutes_left=-1)
        with mock.patch(BACKEND) as get_backend:
            released = storage_sync.release_expired_reservations()

        self.assertEqual(released, 1)
        reservation.refresh_from_db()
        file.refresh_from_db()
        self.assertIsNotNone(file.storage_purged_at)
        self.assertEqual(reservation.status, RELEASED)
        self.assertEqual(file.status, File.Status.DELETED)
        get_backend.return_value.delete_object.assert_called_once_with(storage_key=file.storage_key)

    def test_cleanup_does_not_touch_live_or_confirmed_reservations(self):
        _, live = self.make_upload("viva.pdf", minutes_left=10)
        done_file, done = self.make_upload("lista.pdf", minutes_left=-5, status=CONFIRMED)
        with mock.patch(BACKEND):
            released = storage_sync.release_expired_reservations()

        self.assertEqual(released, 0)
        live.refresh_from_db()
        done.refresh_from_db()
        done_file.refresh_from_db()
        self.assertEqual(live.status, PENDING)
        self.assertEqual(done.status, CONFIRMED)
        self.assertEqual(done_file.status, File.Status.AVAILABLE)

    def test_cleanup_survives_storage_failure(self):
        file, reservation = self.make_upload("vencida.pdf", minutes_left=-1)
        with mock.patch(BACKEND) as get_backend:
            get_backend.return_value.delete_object.side_effect = StorageError("caido")
            with self.assertLogs("files", level="WARNING"):
                released = storage_sync.release_expired_reservations()

        self.assertEqual(released, 1)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, RELEASED)

        file.refresh_from_db()
        self.assertIsNone(file.storage_purged_at)  # quedó pendiente de reintento

    def test_cleanup_frees_the_file_name(self):
        self.make_upload("mismo.pdf", minutes_left=-1)
        with mock.patch(BACKEND):
            storage_sync.release_expired_reservations()

        # El nombre vuelve a estar libre: no debe violar la restricción única.
        self.make_upload("mismo.pdf", minutes_left=10)