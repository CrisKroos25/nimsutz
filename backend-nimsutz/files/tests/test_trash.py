# files/tests/test_trash.py
import uuid
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from files import quota, services
from files.models import File, QuotaReservation

COVERAGE = "files.quota.resolve_effective_subscription"
BACKEND = "files.storage.get_backend"


def coverage(capacity_bytes):
    return SimpleNamespace(plan_version=SimpleNamespace(capacity_bytes=capacity_bytes))


class TrashAndQuotaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            name="Ana", email="ana@example.test", password="Password123!"
        )

    def make_trashed(self, name, size, owner=None):
        owner = owner or self.user
        file = File.objects.create(
            owner=owner, folder=None,
            storage_key=f"{owner.id}/{uuid.uuid4().hex}.pdf",
            original_name=name, content_type="application/pdf", size_bytes=size,
            status=File.Status.TRASHED, trashed_at=timezone.now(),
        )
        QuotaReservation.objects.create(
            owner=owner, file=file, reserved_bytes=size,
            status=QuotaReservation.Status.CONFIRMED, expires_at=timezone.now(),
        )
        return file

    def test_capacity_comes_from_the_effective_coverage(self):
        with mock.patch(COVERAGE, return_value=coverage(5000)) as resolve:
            self.assertEqual(quota.get_capacity_bytes(self.user), 5000)
            resolve.assert_called_with(self.user)

    def test_no_coverage_means_no_capacity(self):
        with mock.patch(COVERAGE, return_value=None):
            self.assertEqual(quota.get_capacity_bytes(self.user), 0)

    def test_trashed_file_still_counts_toward_quota(self):
        self.make_trashed("a.pdf", 400)
        with mock.patch(COVERAGE, return_value=coverage(1000)):
            self.assertEqual(quota.get_used_bytes(self.user), 400)
            self.assertEqual(quota.get_available_quota(self.user), 600)

    def test_restore_does_not_consume_extra_space(self):
        file = self.make_trashed("a.pdf", 400)
        with mock.patch(COVERAGE, return_value=coverage(1000)):
            restored = services.restore_file(file=file, owner=self.user)
            self.assertEqual(restored.status, File.Status.AVAILABLE)
            self.assertIsNone(restored.trashed_at)
            self.assertEqual(quota.get_used_bytes(self.user), 400)

    def test_restore_is_allowed_when_usage_equals_capacity(self):
        file = self.make_trashed("a.pdf", 400)
        with mock.patch(COVERAGE, return_value=coverage(400)):
            services.restore_file(file=file, owner=self.user)
        file.refresh_from_db()
        self.assertEqual(file.status, File.Status.AVAILABLE)

    def test_restore_is_blocked_when_over_capacity(self):
        file = self.make_trashed("a.pdf", 400)
        with mock.patch(COVERAGE, return_value=coverage(300)):  # plan reducido
            with self.assertRaisesMessage(ValidationError, "cuota suficiente"):
                services.restore_file(file=file, owner=self.user)
        file.refresh_from_db()
        self.assertEqual(file.status, File.Status.TRASHED)

    def test_restore_is_blocked_without_coverage(self):
        file = self.make_trashed("a.pdf", 400)
        with mock.patch(COVERAGE, return_value=None):
            with self.assertRaisesMessage(ValidationError, "cuota suficiente"):
                services.restore_file(file=file, owner=self.user)

    def test_permanent_delete_frees_space_and_unblocks_restore(self):
        first = self.make_trashed("a.pdf", 400)
        second = self.make_trashed("b.pdf", 400)

        with mock.patch(COVERAGE, return_value=coverage(500)):  # 800 usados sobre 500
            with self.assertRaises(ValidationError):
                services.restore_file(file=second, owner=self.user)

            with mock.patch(BACKEND):
                services.permanently_delete_file(file=first, owner=self.user)
            self.assertEqual(quota.get_used_bytes(self.user), 400)

            services.restore_file(file=second, owner=self.user)
        second.refresh_from_db()
        self.assertEqual(second.status, File.Status.AVAILABLE)

    def test_cannot_restore_someone_elses_file(self):
        other = get_user_model().objects.create_user(
            name="Luis", email="luis@example.test", password="Password123!"
        )
        file = self.make_trashed("a.pdf", 400)
        with mock.patch(COVERAGE, return_value=coverage(1000)):
            with self.assertRaisesMessage(ValidationError, "no pertenece"):
                services.restore_file(file=file, owner=other)

    def test_restore_with_name_conflict_requires_a_new_name(self):
        file = self.make_trashed("informe.pdf", 400)
        File.objects.create(
            owner=self.user, folder=None, storage_key=f"{self.user.id}/{uuid.uuid4().hex}.pdf",
            original_name="informe.pdf", content_type="application/pdf", size_bytes=10,
            status=File.Status.AVAILABLE,
        )
        with mock.patch(COVERAGE, return_value=coverage(1000)):
            with self.assertRaisesMessage(ValidationError, "nuevo nombre"):
                services.restore_file(file=file, owner=self.user)

            restored = services.restore_file(file=file, owner=self.user, new_name="informe (2).pdf")
        self.assertEqual(restored.original_name, "informe (2).pdf")