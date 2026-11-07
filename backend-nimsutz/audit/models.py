"""Modelo persistente de auditoría administrativa (M21)."""
from django.conf import settings
from django.db import models


class AuditEventQuerySet(models.QuerySet):
    """Los eventos son de solo lectura: ni update ni delete masivos."""

    def update(self, **kwargs):
        raise PermissionError("Los eventos de auditoría no se pueden modificar.")

    def delete(self):
        raise PermissionError("Los eventos de auditoría no se pueden eliminar.")


class AuditEvent(models.Model):
    class Result(models.TextChoices):
        SUCCESS = "success", "Exitoso"
        REJECTED = "rejected", "Rechazado"
        NO_CHANGE = "no_change", "Sin cambios"
        ERROR = "error", "Error"

    # El actor puede desaparecer; el evento conserva id y etiqueta descriptiva.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    actor_ref = models.PositiveBigIntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=64, db_index=True)
    # Referencia descriptiva (no FK): sobrevive a la eliminación de la entidad.
    entity_type = models.CharField(max_length=40, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    result = models.CharField(max_length=16, choices=Result.choices, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise PermissionError("Los eventos de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Los eventos de auditoría no se pueden eliminar.")

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id} [{self.result}]"
