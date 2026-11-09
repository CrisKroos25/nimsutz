"""Servicio único para registrar eventos de auditoría.

Contrato compartido con el resto del módulo de administración:

    record_event(*, actor, action, entity_type, entity_id, result, metadata=None)

Reglas de transacción (las aplica quien llama, no este servicio):
- Cambio exitoso: llamar DENTRO del mismo transaction.atomic() que la mutación.
  Si este servicio falla, la mutación se revierte.
- Rechazo de negocio: llamar DESPUÉS de revertir la transacción de negocio.
- Falla técnica: llamar fuera de la transacción revertida.
"""
from .models import AuditEvent

ACTIONS = frozenset({
    "client.suspended",
    "client.reactivated",
    "plan.version_published",
    "plan.deactivated",
    "administration.access_denied",
})
RESULTS = frozenset(value for value, _ in AuditEvent.Result.choices)
ALLOWED_METADATA_KEYS = frozenset({
    "previous_status", "new_status",
    "previous_version_id", "new_version_id",
    "previous_active", "new_active",
    "plan_code", "version_number", "price", "capacity_bytes",
    "reason_code",
})
MAX_VALUE_LENGTH = 100


class AuditError(ValueError):
    """Evento inválido: nunca se guarda a medias."""


def _clean_metadata(metadata):
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise AuditError("metadata debe ser un diccionario.")
    unknown = set(metadata) - ALLOWED_METADATA_KEYS
    if unknown:
        raise AuditError(f"Claves de metadata no permitidas: {sorted(unknown)}")
    clean = {}
    for key, value in metadata.items():
        if value is not None and not isinstance(value, (str, int, bool)):
            raise AuditError(f"El valor de '{key}' debe ser texto, número, booleano o nulo.")
        if isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
            raise AuditError(f"El valor de '{key}' es demasiado largo.")
        clean[key] = value
    return clean


def record_event(*, actor, action, entity_type, entity_id, result, metadata=None):
    if action not in ACTIONS:
        raise AuditError(f"Acción de auditoría desconocida: {action!r}")
    if result not in RESULTS:
        raise AuditError(f"Resultado de auditoría desconocido: {result!r}")
    entity_type = str(entity_type or "").strip()
    entity_id = str(entity_id if entity_id is not None else "").strip()
    if not entity_type or not entity_id:
        raise AuditError("entity_type y entity_id son obligatorios.")
    if len(entity_type) > 40 or len(entity_id) > 64:
        raise AuditError("La referencia de la entidad es demasiado larga.")
    actor_obj = actor if actor is not None and getattr(actor, "pk", None) else None
    return AuditEvent.objects.create(
        actor=actor_obj,
        actor_ref=actor_obj.pk if actor_obj else None,
        actor_label=(getattr(actor_obj, "email", "") or "")[:254] if actor_obj else "",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        metadata=_clean_metadata(metadata),
    )


def record_access_denied(request):
    """Acceso denegado al módulo de administración (solo usuarios autenticados)."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return None
    return record_event(
        actor=user, action="administration.access_denied",
        entity_type="administration", entity_id=request.path[:64], result="rejected",
        metadata={"reason_code": "not_active_administrator"},
    )
