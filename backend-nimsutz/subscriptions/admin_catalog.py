"""
Servicios de negocio para la administración de catálogo y versiones de planes (M19 - Rodrigo).
Aplica Single Responsibility Principle (SRP) e inmutabilidad estricta de condiciones comerciales.
"""

from decimal import Decimal
import logging
from django.db import transaction

from .audit_integration import record_audit_event
from .errors import SubscriptionError
from .models import Plan, PlanVersion

logger = logging.getLogger(__name__)


def format_plan_version(version: PlanVersion, *, is_current: bool = False, fallback_description: str = "") -> dict:
    """Formatea una versión de plan para consumo administrativo."""
    return {
        "id": version.id,
        "version_number": version.version_number,
        "name": version.name or version.plan.name,
        "description": version.description or fallback_description or getattr(version.plan, "description", ""),
        "price": f"{version.price:.2f}",
        "capacity_bytes": version.capacity_bytes,
        "billing_period": version.billing_period,
        "currency": version.currency,
        "created_at": version.created_at,
        "is_current": is_current,
    }


def list_admin_plans(active: bool = None) -> list[dict]:
    """
    Lista todos los planes configurados para administración, incluyendo versiones vigentes
    y conteo de versiones históricas. Permite filtrar opcionalmente por disponibilidad activa.
    """
    queryset = Plan.objects.all().prefetch_related("versions").order_by("id")

    if active is True:
        queryset = queryset.filter(is_available=True)
    elif active is False:
        queryset = queryset.filter(is_available=False)

    results = []
    for plan in queryset:
        # Ordenar versiones en memoria para optimizar lecturas
        all_versions = sorted(plan.versions.all(), key=lambda v: (v.version_number, v.id), reverse=True)
        latest_version = all_versions[0] if all_versions else None

        current_version_data = None
        if latest_version:
            current_version_data = format_plan_version(
                latest_version,
                is_current=True,
                fallback_description=plan.description,
            )

        results.append(
            {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "description": plan.description,
                "active": plan.is_available,
                "current_version": current_version_data,
                "versions_count": len(all_versions),
                "created_at": plan.created_at,
            }
        )

    return results


def list_plan_versions(plan_id: int) -> dict:
    """
    Obtiene el historial completo de versiones de un plan específico en orden descendente.
    """
    plan = Plan.objects.filter(id=plan_id).first()
    if plan is None:
        raise SubscriptionError("not_found", "Plan no encontrado.")

    versions = plan.versions.all().order_by("-version_number", "-id")
    latest_id = versions[0].id if versions.exists() else None

    formatted_versions = [
        format_plan_version(
            v,
            is_current=(v.id == latest_id),
            fallback_description=plan.description,
        )
        for v in versions
    ]

    return {
        "plan": plan,
        "versions": formatted_versions,
    }


@transaction.atomic
def publish_plan_version(
    *,
    admin_user,
    plan_id: int,
    base_version_id: int,
    name: str = "",
    description: str = "",
    price: Decimal | str | float,
    capacity_bytes: int,
    billing_period: str = None,
) -> dict:
    """
    Publica una nueva versión inmutable de un plan con concurrencia optimista y bloqueo de fila.

    Reglas de negocio:
    - base_version_id debe coincidir exactamente con la última versión vigente (concurrencia optimista).
    - Plan 'free': precio debe ser 0.00 y billing_period nulo/vacío.
    - Planes pagados: precio > 0 y billing_period == 'calendar_month'.
    - capacity_bytes > 0.
    - Emite evento defensivo de auditoría 'plan.version_published'.
    """
    plan = Plan.objects.select_for_update().filter(id=plan_id).first()
    if plan is None:
        raise SubscriptionError("not_found", "Plan no encontrado.")

    latest_version = plan.versions.order_by("-version_number", "-id").first()

    # Verificación de concurrencia optimista
    if latest_version is not None:
        if base_version_id is None or int(base_version_id) != latest_version.id:
            raise SubscriptionError(
                "plan_conditions_changed",
                "Las condiciones del plan cambiaron mientras preparabas la nueva versión. "
                "Por favor actualiza la vista y vuelve a intentar.",
            )

    # Validar precio
    try:
        parsed_price = Decimal(str(price))
    except Exception:
        raise SubscriptionError(
            "invalid_request",
            "El precio proporcionado no es un valor decimal válido.",
            {"price": "Debe ser un número decimal válido."},
        )

    # Validar capacidad
    try:
        parsed_capacity = int(capacity_bytes)
        if parsed_capacity <= 0:
            raise ValueError()
    except Exception:
        raise SubscriptionError(
            "invalid_request",
            "La capacidad en bytes debe ser un número entero mayor a cero.",
            {"capacity_bytes": "Debe ser mayor a 0."},
        )

    # Invariantes Gratis vs Pagado
    if plan.code == "free":
        if parsed_price != Decimal("0.00"):
            raise SubscriptionError(
                "invalid_request",
                "El plan gratuito debe tener un precio de 0.00.",
                {"price": "El precio para el plan gratuito debe ser exactamente 0.00."},
            )
        if billing_period not in (None, ""):
            raise SubscriptionError(
                "invalid_request",
                "El plan gratuito no tiene periodicidad de cobro.",
                {"billing_period": "Debe ser nulo para el plan gratuito."},
            )
        duration_days = None
    else:
        if parsed_price <= Decimal("0.00"):
            raise SubscriptionError(
                "invalid_request",
                "Los planes de pago deben tener un precio mayor a 0.00.",
                {"price": "Debe ser mayor a 0.00."},
            )
        if billing_period != "calendar_month":
            raise SubscriptionError(
                "invalid_request",
                "La periodicidad de cobro para planes de pago debe ser 'calendar_month'.",
                {"billing_period": "Valor permitido: 'calendar_month'."},
            )
        duration_days = 30

    clean_name = (name or "").strip() or plan.name
    clean_description = (description or "").strip()

    next_version_number = (latest_version.version_number + 1) if latest_version else 1

    new_version = PlanVersion.objects.create(
        plan=plan,
        name=clean_name,
        description=clean_description or plan.description,
        version_number=next_version_number,
        price=parsed_price,
        currency="GTQ",
        capacity_bytes=parsed_capacity,
        duration_days=duration_days,
    )

    # Actualizar denominación comercial actual del plan
    plan.name = clean_name
    if clean_description:
        plan.description = clean_description
    plan.save(update_fields=["name", "description", "updated_at"])

    # Auditoría defensiva
    record_audit_event(
        actor=admin_user,
        action="plan.version_published",
        entity_type="plan",
        entity_id=str(plan.id),
        result="success",
        metadata={
            "plan_code": plan.code,
            "previous_version_id": base_version_id,
            "new_version_id": new_version.id,
            "version_number": new_version.version_number,
            "price": str(new_version.price),
            "capacity_bytes": new_version.capacity_bytes,
        },
    )

    return {
        "plan_id": plan.id,
        "version": format_plan_version(new_version, is_current=True),
        "active": plan.is_available,
    }


@transaction.atomic
def deactivate_plan(*, admin_user, plan_id: int) -> dict:
    """
    Desactiva la disponibilidad de un plan para nuevas contrataciones o cambios.
    Los clientes con contratos vigentes en este plan conservan sus derechos de renovación.

    Reglas de negocio:
    - El plan gratuito no puede ser desactivado.
    - Idempotente: si ya estaba inactivo, devuelve changed=False.
    - Emite evento defensivo de auditoría 'plan.deactivated'.
    """
    plan = Plan.objects.select_for_update().filter(id=plan_id).first()
    if plan is None:
        raise SubscriptionError("not_found", "Plan no encontrado.")

    if plan.code == "free":
        raise SubscriptionError(
            "invalid_request",
            "El plan gratuito es el nivel base del sistema y no puede ser desactivado.",
        )

    was_available = plan.is_available
    changed = False

    if was_available:
        plan.is_available = False
        plan.save(update_fields=["is_available", "updated_at"])
        changed = True

        record_audit_event(
            actor=admin_user,
            action="plan.deactivated",
            entity_type="plan",
            entity_id=str(plan.id),
            result="success",
            metadata={
                "plan_code": plan.code,
                "previous_active": was_available,
                "new_active": False,
            },
        )

    return {
        "plan_id": plan.id,
        "active": False,
        "changed": changed,
    }
