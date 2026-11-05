"""
Módulo de integración con el servicio de auditoría (M21 - Miguel).
Provee una interfaz segura y tolerante a fallos para registrar eventos del catálogo
de administración sin bloquear la operación de negocio si el módulo externo no está listo.
"""

import logging

logger = logging.getLogger(__name__)


def record_audit_event(
    *,
    actor=None,
    action: str,
    entity_type: str,
    entity_id: str,
    result: str = "success",
    metadata: dict = None,
) -> None:
    """
    Registra un evento de auditoría invocando el servicio de Miguel si está disponible.
    Firma esperada: record_event(*, actor, action, entity_type, entity_id, result, metadata)
    """
    metadata = metadata or {}
    try:
        from audit.services import record_event  # type: ignore

        record_event(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            result=result,
            metadata=metadata,
        )
    except (ImportError, ModuleNotFoundError):
        logger.info(
            "Servicio de auditoría no disponible; evento '%s' para %s:%s registrado localmente. Metadata: %s",
            action,
            entity_type,
            entity_id,
            metadata,
        )
    except Exception as exc:
        logger.warning(
            "Error no fatal al registrar auditoría de '%s' para %s:%s: %s",
            action,
            entity_type,
            entity_id,
            exc,
            exc_info=True,
        )
