# files/tests.py
"""Pruebas de la subida de archivos a la raíz (folder = None).

Solo se prueban las reglas de `files`. La cuenta y el plan se crean como datos de
apoyo (usuario activo con un plan vigente); aquí no se prueba su lógica.
El almacenamiento (MinIO) se simula, así que estas pruebas no lo necesitan.
"""
import json
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from subscriptions.models import Plan, PlanVersion, Subscription

from files.models import File, Folder, QuotaReservation
from files.services import confirm_upload, request_upload

MB = 1024 * 1024


# ---------- Datos de apoyo ----------

def make_user(email):
    return User.objects.create_user(
        email=email, name=email, password="test-password",
        account_status=User.AccountStatus.ACTIVE, email_verified=True,
    )


def give_active_plan(user, capacity_bytes=100 * MB):
    """Plan vigente con la capacidad indicada (request_upload lo exige)."""
    plan = Plan.objects.create(code=f"test-{user.pk}", name="Test", is_available=True)
    version = PlanVersion.objects.create(
        plan=plan, version_number=1, price=0, currency="GTQ",
        capacity_bytes=capacity_bytes, duration_days=None,
    )
    Subscription.objects.create(user=user, plan_version=version, started_at=timezone.now())


def make_file(owner, folder, name, storage_key, status=File.Status.AVAILABLE):
    return File.objects.create(
        owner=owner, folder=folder, storage_key=storage_key, original_name=name,
        content_type="text/plain", size_bytes=1, status=status,
    )


class RootUploadTestBase(TestCase):
    def setUp(self):
        patcher = patch("files.storage.get_backend")
        self.backend = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.backend.generate_upload_url.return_value = "http://minio.test/upload"

        self.user = make_user("a@example.test")
        self.other = make_user("b@example.test")
        give_active_plan(self.user)
        give_active_plan(self.other)

    def upload(self, user, name="a.txt", size=10, content_type="text/plain", folder=None):
        return request_upload(
            owner=user, folder=folder, original_name=name,
            content_type=content_type, size_bytes=size,
        )


# ---------- Reglas de negocio de la subida a la raíz ----------

class RootUploadRulesTests(RootUploadTestBase):
    def test_upload_at_root_creates_pending_file_and_reservation(self):
        file, url = self.upload(self.user, size=2048)
        self.assertIsNone(file.folder)
        self.assertEqual(file.owner, self.user)
        self.assertEqual(file.status, File.Status.UPLOADING)
        reservation = QuotaReservation.objects.get(file=file)
        self.assertEqual(reservation.status, QuotaReservation.Status.PENDING)
        self.assertEqual(reservation.reserved_bytes, 2048)
        self.assertEqual(url, "http://minio.test/upload")

    def test_storage_key_does_not_depend_on_file_name(self):  # RN-E3-20
        file, _ = self.upload(self.user, name="informe final.PDF", content_type="application/pdf")
        self.assertTrue(file.storage_key.startswith(f"{self.user.id}/"))
        self.assertTrue(file.storage_key.endswith(".pdf"))
        self.assertNotIn("informe", file.storage_key)

    def test_duplicate_name_at_root_rejected_ignoring_case_and_spaces(self):  # RN-E3-11/15/16
        self.upload(self.user, name="Reporte.txt")
        with self.assertRaises(ValidationError):
            self.upload(self.user, name="  reporte.TXT ")

    def test_same_name_at_root_allowed_for_different_users(self):
        self.upload(self.user)
        self.upload(self.other)  # no debe lanzar

    def test_same_name_allowed_at_root_and_inside_a_folder(self):
        folder = Folder.objects.create(owner=self.user, parent=None, name="Docs")
        self.upload(self.user)
        self.upload(self.user, folder=folder)  # distinta ubicación: no debe lanzar

    def test_name_of_trashed_file_can_be_reused_at_root(self):  # RN-E3-29
        make_file(self.user, None, "a.txt", "k/old", status=File.Status.TRASHED)
        self.upload(self.user, name="a.txt")  # no debe lanzar

    def test_disallowed_type_rejected(self):  # RN-E3-18
        with self.assertRaises(ValidationError):
            self.upload(self.user, name="a.zip", content_type="application/zip")

    def test_size_limits_enforced(self):  # RN-E3-17
        for size in (0, settings.MAX_FILE_SIZE_BYTES + 1):
            with self.subTest(size=size), self.assertRaises(ValidationError):
                self.upload(self.user, size=size)

    def test_pending_reservations_count_against_quota(self):  # RN-E3-25/26
        small = make_user("s@example.test")
        give_active_plan(small, capacity_bytes=10 * MB)
        self.upload(small, name="a.txt", size=6 * MB)
        with self.assertRaises(ValidationError):
            self.upload(small, name="b.txt", size=6 * MB)  # solo quedan 4 MB

    def test_folder_of_another_user_still_rejected(self):  # RN-E3-04/05
        foreign = Folder.objects.create(owner=self.other, parent=None, name="Ajena")
        with self.assertRaises(ValidationError):
            self.upload(self.user, folder=foreign)

    def test_confirming_an_upload_at_root_makes_it_available(self):
        file, _ = self.upload(self.user, size=1024)
        self.backend.head_object.return_value = {"ContentLength": 1024, "ContentType": "text/plain",}
        confirmed = confirm_upload(file=file, owner=self.user)
        self.assertEqual(confirmed.status, File.Status.AVAILABLE)
        self.assertEqual(
            QuotaReservation.objects.get(file=file).status, QuotaReservation.Status.CONFIRMED
        )

    def test_database_rejects_duplicate_root_names_per_owner(self):
        self.upload(self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_file(self.user, None, "a.txt", "k/dup")
        make_file(self.other, None, "a.txt", "k/other")  # otro usuario: permitido


# ---------- Mismo flujo a través de la API ----------

class RootUploadApiTests(RootUploadTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def post_upload(self, **extra):
        payload = {"original_name": "a.txt", "content_type": "text/plain", "size_bytes": 10, **extra}
        return self.client.post(
            "/api/files/request-upload/", data=json.dumps(payload), content_type="application/json"
        )

    def test_folder_null_uploads_to_root(self):
        response = self.post_upload(folder=None)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["file"]["folder"])

    def test_omitting_folder_uploads_to_root(self):
        response = self.post_upload()
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["file"]["folder"])

    def test_duplicate_name_at_root_returns_400(self):
        self.assertEqual(self.post_upload().status_code, 201)
        self.assertEqual(self.post_upload().status_code, 400)

    def test_root_listing_returns_only_own_available_root_files(self):
        folder = Folder.objects.create(owner=self.user, parent=None, name="Docs")
        make_file(self.user, None, "root.txt", "k/root")
        make_file(self.user, folder, "inside.txt", "k/inside")
        make_file(self.user, None, "gone.txt", "k/gone", status=File.Status.TRASHED)
        make_file(self.other, None, "other.txt", "k/other")
        response = self.client.get("/api/files/?folder=root")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([f["original_name"] for f in response.json()], ["root.txt"])