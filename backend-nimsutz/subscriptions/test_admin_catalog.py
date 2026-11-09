"""
Suite completa de pruebas automatizadas para el catálogo administrativo versionado (M19 - Rodrigo).
Valida inmutabilidad, control de concurrencia optimista (409), permisos administrativos (403),
paginación, reglas de negocio para planes Gratis vs. Pagados, y desactivación sin afectar renovaciones.
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from audit.models import AuditEvent
from .errors import SubscriptionError
from .models import Plan, PlanVersion, Subscription
from . import services


def create_admin_user(email="admin@nimsutz.local", **extra):
    return User.objects.create_superuser(
        email=email,
        name="Admin Test",
        password="admin-password-123",
        **extra,
    )


def create_client_user(email="cliente@nimsutz.local", **extra):
    return User.objects.create_user(
        email=email,
        name="Cliente Test",
        password="client-password-123",
        account_status=User.AccountStatus.ACTIVE,
        email_verified=True,
        **extra,
    )


class AdminAccessControlTests(TestCase):
    """Verifica que solo administradores activos y verificados tengan acceso (RN y R1)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.admin = create_admin_user()
        cls.client_user = create_client_user()
        cls.suspended_admin = create_admin_user(
            email="suspended_admin@nimsutz.local",
            account_status=User.AccountStatus.SUSPENDED,
        )
        cls.unverified_admin = create_admin_user(
            email="unverified_admin@nimsutz.local",
            email_verified=False,
            account_status=User.AccountStatus.PENDING_VERIFICATION,
        )

    def test_anonymous_user_is_denied(self):
        resp = self.client.get("/api/administration/plans/")
        self.assertIn(resp.status_code, [401, 403])

    def test_client_role_is_denied_with_403(self):
        self.client.force_login(self.client_user)
        resp = self.client.get("/api/administration/plans/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("code"), "forbidden")

    def test_suspended_admin_is_denied_with_403(self):
        self.client.force_login(self.suspended_admin)
        resp = self.client.get("/api/administration/plans/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("code"), "forbidden")

    def test_unverified_admin_is_denied_with_403(self):
        self.client.force_login(self.unverified_admin)
        resp = self.client.get("/api/administration/plans/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("code"), "forbidden")

    def test_active_admin_is_authorized(self):
        self.client.force_login(self.admin)
        resp = self.client.get("/api/administration/plans/")
        self.assertEqual(resp.status_code, 200)


class AdminPlanListApiTests(TestCase):
    """Verifica el listado de planes, estructura paginada y filtros de disponibilidad."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.admin = create_admin_user()

    def setUp(self):
        self.client.force_login(self.admin)

    def test_list_plans_returns_paginated_format(self):
        resp = self.client.get("/api/administration/plans/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 3)

        free_plan = next(p for p in data["results"] if p["code"] == "free")
        self.assertEqual(free_plan["name"], "Gratis")
        self.assertTrue(free_plan["active"])
        self.assertEqual(free_plan["versions_count"], 1)

        cv = free_plan["current_version"]
        self.assertIsNotNone(cv)
        self.assertEqual(cv["version_number"], 1)
        self.assertEqual(cv["price"], "0.00")
        self.assertIsNone(cv["billing_period"])
        self.assertTrue(cv["is_current"])

    def test_filter_by_active_status(self):
        # Desactivar plan basic
        Plan.objects.filter(code="basic").update(is_available=False)

        # Filtrar active=true
        resp_active = self.client.get("/api/administration/plans/?active=true")
        self.assertEqual(resp_active.status_code, 200)
        data_active = resp_active.json()
        self.assertEqual(data_active["count"], 2)
        codes = [p["code"] for p in data_active["results"]]
        self.assertNotIn("basic", codes)

        # Filtrar active=false
        resp_inactive = self.client.get("/api/administration/plans/?active=false")
        self.assertEqual(resp_inactive.status_code, 200)
        data_inactive = resp_inactive.json()
        self.assertEqual(data_inactive["count"], 1)
        self.assertEqual(data_inactive["results"][0]["code"], "basic")


class AdminPlanVersionHistoryApiTests(TestCase):
    """Verifica el historial de versiones en solo lectura de un plan."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.admin = create_admin_user()
        cls.basic_plan = Plan.objects.get(code="basic")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_version_history_sorted_and_marks_current(self):
        v1 = self.basic_plan.versions.get(version_number=1)
        # Crear versión 2
        v2 = PlanVersion.objects.create(
            plan=self.basic_plan,
            version_number=2,
            name="Básico 2.0",
            description="Mejora de almacenamiento",
            price=Decimal("18.00"),
            capacity_bytes=1500 * 1024 * 1024,
            duration_days=30,
        )

        resp = self.client.get(f"/api/administration/plans/{self.basic_plan.id}/versions/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 2)

        results = data["results"]
        # La primera debe ser la versión más reciente (v2)
        self.assertEqual(results[0]["version_number"], 2)
        self.assertTrue(results[0]["is_current"])
        self.assertEqual(results[0]["price"], "18.00")

        # La segunda debe ser la versión anterior (v1)
        self.assertEqual(results[1]["version_number"], 1)
        self.assertFalse(results[1]["is_current"])
        self.assertEqual(results[1]["price"], "15.00")

    def test_version_history_not_found(self):
        resp = self.client.get("/api/administration/plans/99999/versions/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json().get("code"), "not_found")


class AdminPublishVersionApiTests(TestCase):
    """Verifica la publicación de nuevas versiones, concurrencia optimista y validaciones."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.admin = create_admin_user()
        cls.basic_plan = Plan.objects.get(code="basic")
        cls.free_plan = Plan.objects.get(code="free")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_publish_new_version_success(self):
        current_v1 = self.basic_plan.versions.get(version_number=1)
        payload = {
            "base_version_id": current_v1.id,
            "name": "Básico Mejorado",
            "description": "2 GB de almacenamiento garantizado.",
            "price": "20.00",
            "capacity_bytes": 2 * 1024 * 1024 * 1024,
            "billing_period": "calendar_month",
        }
        resp = self.client.post(
            f"/api/administration/plans/{self.basic_plan.id}/versions/",
            payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["plan_id"], self.basic_plan.id)
        self.assertEqual(data["version"]["version_number"], 2)
        self.assertEqual(data["version"]["name"], "Básico Mejorado")
        self.assertEqual(data["version"]["price"], "20.00")
        self.assertTrue(data["version"]["is_current"])
        event = AuditEvent.objects.get(action="plan.version_published", entity_id=str(self.basic_plan.id))
        self.assertEqual(event.metadata["plan_code"], "basic")
        self.assertEqual(event.metadata["version_number"], 2)

        # Verificar que v1 permanece inalterada
        current_v1.refresh_from_db()
        self.assertEqual(current_v1.version_number, 1)
        self.assertEqual(current_v1.price, Decimal("15.00"))

        # Verificar que el plan actualizó su branding
        self.basic_plan.refresh_from_db()
        self.assertEqual(self.basic_plan.name, "Básico Mejorado")

    def test_optimistic_concurrency_conflict_409(self):
        v1 = self.basic_plan.versions.get(version_number=1)

        # Simulamos que otro administrador publicó v2
        services.publish_plan_version(
            admin_user=self.admin,
            plan_id=self.basic_plan.id,
            base_version_id=v1.id,
            name="Versión Intermedia",
            description="Cambio por otro admin",
            price="16.00",
            capacity_bytes=1100 * 1024 * 1024,
            billing_period="calendar_month",
        )

        # Ahora un segundo admin intenta publicar basándose en la v1 obsoleta
        stale_payload = {
            "base_version_id": v1.id,  # versión desfasada
            "name": "Intento Desfasado",
            "description": "No debería pasar",
            "price": "22.00",
            "capacity_bytes": 2048 * 1024 * 1024,
            "billing_period": "calendar_month",
        }
        resp = self.client.post(
            f"/api/administration/plans/{self.basic_plan.id}/versions/",
            stale_payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        data = resp.json()
        self.assertEqual(data.get("code"), "plan_conditions_changed")

    def test_publishing_new_version_invalidates_stale_quotations(self):
        """
        Requisito de la guía: Reutilizar las comprobaciones comerciales para que
        una cotización antigua no permita contratar condiciones que ya cambiaron.
        """
        client = create_client_user(email="buyer@nimsutz.local")
        v1 = self.basic_plan.versions.get(version_number=1)

        # Cliente cotiza bajo la versión 1
        quote = services.prepare_quote(user=client, operation="contract", plan_version_id=v1.id)
        self.assertEqual(quote.plan_version.id, v1.id)

        # Administrador publica versión 2
        services.publish_plan_version(
            admin_user=self.admin,
            plan_id=self.basic_plan.id,
            base_version_id=v1.id,
            name="Básico Plus",
            price="18.00",
            capacity_bytes=1500 * 1024 * 1024,
            billing_period="calendar_month",
        )

        # Al intentar validar la cotización previa, el motor comercial lo rechaza con 409
        with self.assertRaises(SubscriptionError) as ctx:
            services.validate_quote_for_execution(user=client, quote_id=quote.id)
        self.assertEqual(ctx.exception.code, "plan_conditions_changed")

    def test_free_plan_requires_price_zero(self):
        v1 = self.free_plan.versions.get(version_number=1)
        payload = {
            "base_version_id": v1.id,
            "name": "Gratis Ilegal",
            "description": "Gratis no puede costar",
            "price": "5.00",
            "capacity_bytes": 150 * 1024 * 1024,
            "billing_period": None,
        }
        resp = self.client.post(
            f"/api/administration/plans/{self.free_plan.id}/versions/",
            payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "invalid_request")

    def test_paid_plan_requires_price_greater_than_zero(self):
        v1 = self.basic_plan.versions.get(version_number=1)
        payload = {
            "base_version_id": v1.id,
            "name": "Básico Gratis Ilegal",
            "description": "Plan comercial no puede ser 0",
            "price": "0.00",
            "capacity_bytes": 1024 * 1024 * 1024,
            "billing_period": "calendar_month",
        }
        resp = self.client.post(
            f"/api/administration/plans/{self.basic_plan.id}/versions/",
            payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "invalid_request")

    def test_capacity_bytes_must_be_positive(self):
        v1 = self.basic_plan.versions.get(version_number=1)
        payload = {
            "base_version_id": v1.id,
            "name": "Básico Cero",
            "description": "Sin espacio",
            "price": "15.00",
            "capacity_bytes": 0,
            "billing_period": "calendar_month",
        }
        resp = self.client.post(
            f"/api/administration/plans/{self.basic_plan.id}/versions/",
            payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "invalid_request")


class AdminDeactivatePlanApiTests(TestCase):
    """Verifica desactivación de planes, idempotencia e invariantes de contratos."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.admin = create_admin_user()
        cls.basic_plan = Plan.objects.get(code="basic")
        cls.free_plan = Plan.objects.get(code="free")
        cls.client_user = create_client_user()

    def setUp(self):
        self.client.force_login(self.admin)

    def test_deactivate_paid_plan_success_and_idempotent(self):
        resp = self.client.post(f"/api/administration/plans/{self.basic_plan.id}/deactivate/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["plan_id"], self.basic_plan.id)
        self.assertFalse(data["active"])
        self.assertTrue(data["changed"])
        event = AuditEvent.objects.get(action="plan.deactivated", entity_id=str(self.basic_plan.id))
        self.assertEqual(event.metadata["plan_code"], "basic")

        self.basic_plan.refresh_from_db()
        self.assertFalse(self.basic_plan.is_available)

        # Llamar de nuevo es idempotente
        resp2 = self.client.post(f"/api/administration/plans/{self.basic_plan.id}/deactivate/")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertFalse(data2["active"])
        self.assertFalse(data2["changed"])

    def test_free_plan_cannot_be_deactivated(self):
        resp = self.client.post(f"/api/administration/plans/{self.free_plan.id}/deactivate/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "invalid_request")

        self.free_plan.refresh_from_db()
        self.assertTrue(self.free_plan.is_available)

    def test_deactivated_plan_preserves_existing_contract_renewals(self):
        """
        Regla crítica de negocio: al desactivar un plan, los clientes existentes con
        contratos en dicho plan conservan su derecho a renovar su versión contratada.
        """
        basic_version = self.basic_plan.versions.first()
        now = timezone.now()
        sub = Subscription.objects.create(
            user=self.client_user,
            plan_version=basic_version,
            status=Subscription.Status.ACTIVE,
            started_at=now,
            expires_at=now + timezone.timedelta(days=30),
            cycle_anchor_day=now.day,
            coverage_end=now + timezone.timedelta(days=30),
            selected_plan_version=basic_version,
            selected_at=now,
            selected_conditions={"plan_code": "basic", "price": "15.00", "version_id": basic_version.id},
        )

        # Administrador desactiva el plan básico
        services.deactivate_plan(admin_user=self.admin, plan_id=self.basic_plan.id)
        self.basic_plan.refresh_from_db()
        self.assertFalse(self.basic_plan.is_available)

        # La suscripción existente sigue activa y resolviendo cobertura
        effective = services.resolve_effective_subscription(self.client_user)
        self.assertIsNotNone(effective)
        self.assertEqual(effective.plan_version.id, basic_version.id)

        # Los contratos existentes pueden renovar su versión aunque el plan
        # ya no esté disponible para nuevas contrataciones.
        quote = services.prepare_quote(user=self.client_user, operation="renew")
        self.assertEqual(quote.operation, "renew")
        self.assertEqual(quote.plan_version_id, basic_version.id)


class PlanVersionImmutabilityModelTests(TestCase):
    """Verifica inmutabilidad estricta a nivel ORM para PlanVersion."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_plans")
        cls.plan = Plan.objects.get(code="basic")
        cls.version = cls.plan.versions.first()

    def test_orm_blocks_editing_published_version(self):
        self.version.price = Decimal("99.99")
        with self.assertRaises(ValidationError):
            self.version.save()

    def test_orm_blocks_deleting_published_version(self):
        with self.assertRaises(ValidationError):
            self.version.delete()
