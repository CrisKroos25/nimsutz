"""M10: validar nombres sin modificar carpetas ante entradas inválidas."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from files.models import Folder
from files.services import create_folder, rename_folder


class FolderNameTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            email="folders@example.test", name="Carpetas", email_verified=True,
            account_status="activa",
        )
        cls.other = get_user_model().objects.create_user(
            email="other-folders@example.test", name="Otra cuenta", email_verified=True,
            account_status="activa",
        )
        cls.folder = Folder.objects.create(owner=cls.owner, name="Original")
        cls.limit = Folder._meta.get_field("name").max_length

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def rename(self, value):
        return self.api.patch(f"/api/folders/{self.folder.pk}/", {"name": value}, format="json")

    def test_invalid_inputs_return_400_without_changing_existing_data(self):
        invalid = ["", "   ", "\t\n", None, 123, 1.5, True, [], {},
                   "x" * (self.limit + 1), "nombre\x00inválido"]
        for value in invalid:
            with self.subTest(value=repr(value)):
                count = Folder.objects.count()
                created = self.api.post("/api/folders/", {"name": value}, format="json")
                renamed = self.rename(value)
                for response in (created, renamed):
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn("name", response.data)
                self.folder.refresh_from_db()
                self.assertEqual(self.folder.name, "Original")
                self.assertEqual(Folder.objects.count(), count)

    def test_missing_name_is_required_for_create_and_rename(self):
        for method, url in (("post", "/api/folders/"), ("patch", f"/api/folders/{self.folder.pk}/")):
            response = getattr(self.api, method)(url, {}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("name", response.data)

    def test_normalizes_spaces_and_preserves_unicode_for_both_operations(self):
        response = self.api.post("/api/folders/", {"name": "  Diseño preliminar  "}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Diseño preliminar")
        response = self.rename("  Información útil  ")
        self.assertEqual(response.status_code, 200)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Información útil")

    def test_maximum_length_is_valid_after_normalizing_spaces(self):
        name = "á" * self.limit
        response = self.api.post("/api/folders/", {"name": f" {name} "}, format="json")
        self.assertEqual(response.status_code, 201)
        Folder.objects.filter(pk=response.data["id"]).delete()
        self.assertEqual(self.rename(f" {name} ").status_code, 200)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, name)

    def test_duplicate_name_ignores_case_and_surrounding_spaces(self):
        Folder.objects.create(owner=self.owner, name="Documentos")
        response = self.rename("  DOCUMENTOS  ")
        self.assertEqual(response.status_code, 400)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Original")
        response = self.api.post("/api/folders/", {"name": " documentos "}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_same_name_remains_valid_for_different_locations_or_owners(self):
        parent = Folder.objects.create(owner=self.owner, name="Padre")
        Folder.objects.create(owner=self.owner, parent=parent, name="Compartido")
        Folder.objects.create(owner=self.other, name="Compartido")
        self.assertEqual(self.rename("Compartido").status_code, 200)

    def test_renaming_to_own_name_is_idempotent(self):
        for _ in range(2):
            self.assertEqual(self.rename(" Original ").status_code, 200)
        self.assertEqual(Folder.objects.filter(owner=self.owner).count(), 1)

    def test_other_account_cannot_rename_the_folder(self):
        self.api.force_authenticate(self.other)
        self.assertEqual(self.rename("Ajena").status_code, 404)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Original")

    def test_services_reject_invalid_names_without_serializer(self):
        for value in (None, 12, False, [], {}, "   ", "x" * (self.limit + 1), "a\x00b"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValidationError):
                    create_folder(owner=self.owner, parent=None, name=value)
                with self.assertRaises(ValidationError):
                    rename_folder(folder=self.folder, new_name=value)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, "Original")
        self.assertEqual(Folder.objects.filter(owner=self.owner).count(), 1)
