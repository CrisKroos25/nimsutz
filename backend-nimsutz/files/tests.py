from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from .models import File, Folder, QuotaReservation
from .services import confirm_upload, get_used_bytes, release_expired_uploads

MB = 1024 * 1024


class ReservationLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="f@example.test", name="F", password="test-password",
            account_status=User.AccountStatus.ACTIVE, email_verified=True,
        )
        self.folder = Folder.objects.create(owner=self.user, parent=None, name="Docs")

    def stale_upload(self, size=10 * MB):
        file = File.objects.create(
            owner=self.user, folder=self.folder, storage_key="1/abc.txt",
            original_name="a.txt", content_type="text/plain",
            size_bytes=size, status=File.Status.UPLOADING,
        )
        QuotaReservation.objects.create(
            owner=self.user, file=file, reserved_bytes=size,
            status=QuotaReservation.Status.PENDING,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        return file

    def test_expired_pending_reservation_does_not_count(self):
        self.stale_upload()
        self.assertEqual(get_used_bytes(self.user), 0)

    @patch("files.services.storage.get_backend")
    def test_release_frees_name_reservation_and_orphan_object(self, get_backend):
        file = self.stale_upload()
        release_expired_uploads(owner=self.user)
        self.assertFalse(File.objects.filter(pk=file.pk).exists())
        self.assertEqual(QuotaReservation.objects.get().status, QuotaReservation.Status.RELEASED)
        get_backend.return_value.delete_object.assert_called_once_with(storage_key="1/abc.txt")

    @patch("files.services.storage.get_backend")
    def test_expired_reservation_cannot_be_confirmed(self, get_backend):
        file = self.stale_upload()
        with self.assertRaises(ValidationError):
            confirm_upload(file=file, owner=self.user)
        self.assertFalse(File.objects.filter(pk=file.pk).exists())
        get_backend.return_value.head_object.assert_not_called()