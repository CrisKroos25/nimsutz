"""
Módulo de integración con el servicio de auditoría (M21 - Miguel).
Provee una interfaz segura y tolerante a fallos para registrar eventos del catálogo
de administración sin bloquear la operación de negocio si el módulo externo no está listo.
"""

import logging

logger = logging.getLogger(__name__)


def _get_record_event_func():
    """Intenta localizar el helper de registro de auditoría de Miguel."""
    modules_to_try = [
        ("audit.services", "record_event"),
        ("audit", "record_event"),
        ("audit.recorder", "record_event"),
        ("audit.models", "record_event"),
    ]
    for mod_name, func_name in modules_to_try:
        try:
            mod = __import__(mod_name, fromlist=[func_name])
            func = getattr(mod, func_name, None)
            if callable(func):
                return func
        except (ImportError, ModuleNotFoundError):
            continue
    return None


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
    record_event_fn = _get_record_event_func()

    if record_event_fn is not None:
        try:
            record_event_fn(
                actor=actor,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                result=result,
                metadata=metadata,
            )
            return
        except Exception as exc:
            logger.warning(
                "Error no fatal al ejecutar auditoría externa de '%s' para %s:%s: %s",
                action,
                entity_type,
                entity_id,
                exc,
                exc_info=True,
            )

    logger.info(
        "Evento de auditoría registrado localmente: acción='%s', entidad=%s:%s, actor=%s, metadata=%s",
        action,
        entity_type,
        entity_id,
        getattr(actor, "email", str(actor)),
        metadata,
    )
