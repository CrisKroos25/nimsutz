from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from subscriptions import services as subscription_services
from subscriptions.models import Subscription

from .models import File, Folder, QuotaReservation
from .services import (
    confirm_upload,
    get_available_quota,
    get_capacity_bytes,
    get_used_bytes,
    permanently_delete_file,
    request_download,
    request_upload,
    restore_file,
    trash_file,
)

MB = 1024 * 1024
FREE_BYTES = 100 * MB


def make_user(email):
    return User.objects.create_user(
        email=email, name=email, password="test-password",
        account_status=User.AccountStatus.ACTIVE, email_verified=True,
    )


def upload(user, folder, name, size):
    """Sube y confirma un archivo completo con el almacenamiento simulado."""
    with patch("files.services.storage.get_backend") as get_backend:
        backend = get_backend.return_value
        backend.generate_upload_url.return_value = "http://storage.test/put"
        file, _ = request_upload(
            owner=user, folder=folder, original_name=name,
            content_type="text/plain", size_bytes=size,
        )
        backend.head_object.return_value = {"ContentLength": size}
        return confirm_upload(file=file, owner=user)


class CoverageQuotaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.user = make_user("cuota@example.test")
        cls.folder = Folder.objects.create(owner=cls.user, parent=None, name="Docs")

    def request_without_confirming(self, size, name="a.txt"):
        with patch("files.services.storage.get_backend") as get_backend:
            get_backend.return_value.generate_upload_url.return_value = "http://storage.test/put"
            return request_upload(
                owner=self.user, folder=self.folder, original_name=name,
                content_type="text/plain", size_bytes=size,
            )

    # --- sin plan no hay almacenamiento ---

    def test_user_without_plan_has_no_capacity(self):
        self.assertEqual(get_capacity_bytes(self.user), 0)
        self.assertEqual(get_available_quota(self.user), 0)

    def test_user_without_plan_cannot_upload_and_nothing_is_created(self):
        with self.assertRaises(ValidationError):
            self.request_without_confirming(1 * MB)
        self.assertEqual(File.objects.count(), 0)
        self.assertEqual(QuotaReservation.objects.count(), 0)

    @override_settings(SIMULATED_QUOTA_BYTES=500 * MB)
    def test_global_simulated_quota_no_longer_grants_space(self):
        with self.assertRaises(ValidationError):
            self.request_without_confirming(1 * MB)

    def test_preference_alone_does_not_grant_space(self):
        premium = subscription_services.get_current_version("premium")
        subscription_services.set_preference(user=self.user, plan_version_id=premium.pk)
        self.assertEqual(get_capacity_bytes(self.user), 0)
        with self.assertRaises(ValidationError):
            self.request_without_confirming(1 * MB)

    # --- plan Gratis = 100 MB ---

    def test_free_plan_gives_100mb(self):
        subscription_services.activate_free(user=self.user)
        self.assertEqual(get_capacity_bytes(self.user), FREE_BYTES)
        self.assertEqual(get_available_quota(self.user), FREE_BYTES)

    @override_settings(SIMULATED_QUOTA_BYTES=1)
    def test_capacity_comes_from_plan_not_from_simulated_setting(self):
        subscription_services.activate_free(user=self.user)
        file = upload(self.user, self.folder, "a.txt", 10 * MB)
        self.assertEqual(file.status, File.Status.AVAILABLE)

    def test_upload_up_to_the_limit_is_accepted_and_one_more_byte_rejected(self):
        subscription_services.activate_free(user=self.user)
        for i in range(4):
            upload(self.user, self.folder, f"f{i}.txt", 25 * MB)
        self.assertEqual(get_used_bytes(self.user), FREE_BYTES)
        self.assertEqual(get_available_quota(self.user), 0)
        with self.assertRaises(ValidationError):
            self.request_without_confirming(1, name="extra.txt")
        self.assertEqual(File.objects.count(), 4)

    def test_pending_reservation_counts_against_the_limit(self):
        subscription_services.activate_free(user=self.user)
        for i in range(3):
            upload(self.user, self.folder, f"f{i}.txt", 25 * MB)
        self.request_without_confirming(25 * MB, name="pendiente.txt")
        with self.assertRaises(ValidationError):
            self.request_without_confirming(1, name="otro.txt")

    def test_trashed_files_keep_consuming_space(self):
        subscription_services.activate_free(user=self.user)
        file = upload(self.user, self.folder, "a.txt", 25 * MB)
        trash_file(file=file, owner=self.user)
        self.assertEqual(get_used_bytes(self.user), 25 * MB)
        self.assertEqual(get_available_quota(self.user), FREE_BYTES - 25 * MB)

    def test_permanent_delete_frees_space(self):
        subscription_services.activate_free(user=self.user)
        file = upload(self.user, self.folder, "a.txt", 25 * MB)
        trash_file(file=file, owner=self.user)
        with patch("files.services.storage.get_backend"):
            permanently_delete_file(file=file, owner=self.user)
        self.assertEqual(get_used_bytes(self.user), 0)
        self.assertEqual(get_available_quota(self.user), FREE_BYTES)

    def test_quota_is_per_owner(self):
        other = make_user("otro@example.test")
        other_folder = Folder.objects.create(owner=other, parent=None, name="Docs")
        subscription_services.activate_free(user=self.user)
        subscription_services.activate_free(user=other)
        upload(self.user, self.folder, "a.txt", 25 * MB)
        self.assertEqual(get_available_quota(other), FREE_BYTES)
        upload(other, other_folder, "a.txt", 25 * MB)
        self.assertEqual(get_used_bytes(self.user), 25 * MB)
        self.assertEqual(get_used_bytes(other), 25 * MB)

    def test_covered_user_and_uncovered_user_do_not_affect_each_other(self):
        other = make_user("sinplan@example.test")
        other_folder = Folder.objects.create(owner=other, parent=None, name="Docs")
        subscription_services.activate_free(user=self.user)
        with self.assertRaises(ValidationError):
            request_upload(
                owner=other, folder=other_folder, original_name="a.txt",
                content_type="text/plain", size_bytes=1 * MB,
            )
        self.assertEqual(get_capacity_bytes(self.user), FREE_BYTES)

    def test_paid_plan_capacity_comes_from_its_version(self):
        version = subscription_services.get_current_version("basic")
        Subscription.objects.create(
            user=self.user, plan_version=version, started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.assertEqual(get_capacity_bytes(self.user), 1024 * MB)


class DataConservationTests(TestCase):
    """Perder la cobertura no borra ni oculta lo ya almacenado."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.user = make_user("datos@example.test")
        cls.folder = Folder.objects.create(owner=cls.user, parent=None, name="Docs")

    def setUp(self):
        version = subscription_services.get_current_version("basic")
        self.subscription = Subscription.objects.create(
            user=self.user, plan_version=version, started_at=timezone.now() - timedelta(days=31),
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.file = upload(self.user, self.folder, "a.txt", 10 * MB)
        self.trashed = upload(self.user, self.folder, "b.txt", 5 * MB)
        trash_file(file=self.trashed, owner=self.user)
        Subscription.objects.filter(pk=self.subscription.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.subscription.refresh_from_db()
        self.subscription.coverage_history.filter(state='valid').update(
            ends_at=self.subscription.expires_at, cycle_ends_at=self.subscription.expires_at)


    def test_expired_subscription_returns_to_free_capacity(self):
        self.assertEqual(get_capacity_bytes(self.user), 100 * MB)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(self.subscription.plan_version.plan.code, "free")

    def test_return_to_free_allows_upload_within_free_quota(self):
        request_upload(
            owner=self.user, folder=self.folder, original_name="nuevo.txt",
            content_type="text/plain", size_bytes=1,
        )
        self.assertEqual(get_capacity_bytes(self.user), 100 * MB)

    def test_files_and_reservations_are_untouched(self):
        self.assertEqual(File.objects.filter(owner=self.user).count(), 2)
        self.file.refresh_from_db()
        self.trashed.refresh_from_db()
        self.assertEqual(self.file.status, File.Status.AVAILABLE)
        self.assertEqual(self.trashed.status, File.Status.TRASHED)
        self.assertEqual(get_used_bytes(self.user), 15 * MB)
        self.assertEqual(
            QuotaReservation.objects.filter(
                owner=self.user, status=QuotaReservation.Status.CONFIRMED
            ).count(),
            2,
        )

    def test_existing_files_can_still_be_downloaded(self):
        with patch("files.services.storage.get_backend") as get_backend:
            get_backend.return_value.generate_download_url.return_value = "http://storage.test/get"
            url = request_download(file=self.file, owner=self.user)
        self.assertEqual(url, "http://storage.test/get")

    def test_trashed_file_can_still_be_permanently_deleted_after_expiry(self):
        with patch("files.services.storage.get_backend"):
            permanently_delete_file(file=self.trashed, owner=self.user)
        self.assertEqual(get_used_bytes(self.user), 10 * MB)

    def test_reactivating_coverage_restores_the_ability_to_upload(self):
        subscription_services.activate_free(user=self.user)
        self.assertEqual(get_capacity_bytes(self.user), FREE_BYTES)
        extra = upload(self.user, self.folder, "nuevo.txt", 1 * MB)
        self.assertEqual(extra.status, File.Status.AVAILABLE)
        self.assertEqual(get_used_bytes(self.user), 16 * MB)
