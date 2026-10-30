# files/test_concurrency.py
import threading
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase, override_settings

from files import quota, services, storage_sync


@override_settings(
    ALLOWED_CONTENT_TYPES=["application/pdf"],
    MAX_FILE_SIZE_BYTES=10_000,
    RESERVATION_TTL_MINUTES=10,
)
class ConcurrentUploadRequestTests(TransactionTestCase):
    def test_two_simultaneous_requests_cannot_exceed_capacity(self):
        user = get_user_model().objects.create_user(
            name="Ana", email="ana@example.test", password="Password123!"
        )
        # Capacidad 1000 bytes; cada solicitud pide 600, así que solo una cabe.
        subscription = SimpleNamespace(plan_version=SimpleNamespace(capacity_bytes=1000))
        results = []
        barrier = threading.Barrier(2)

        def attempt(name):
            try:
                barrier.wait()
                services.request_upload(
                    owner=user, folder=None, original_name=name,
                    content_type="application/pdf", size_bytes=600,
                )
                results.append("ok")
            except ValidationError:
                results.append("rechazada")
            except Exception as exc:  # cualquier otro error debe verse en el fallo del test
                results.append(repr(exc))
            finally:
                connection.close()

        with mock.patch("files.quota.resolve_effective_subscription", return_value=subscription), \
            mock.patch("files.quota.resolve_effective_subscription", return_value=subscription), \
            mock.patch("files.storage.get_backend") as get_backend:
            get_backend.return_value.generate_upload_url.return_value = "http://minio.test/upload"
            threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a.pdf", "b.pdf")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(sorted(results), ["ok", "rechazada"])
        self.assertEqual(quota.get_used_bytes(user), 600)