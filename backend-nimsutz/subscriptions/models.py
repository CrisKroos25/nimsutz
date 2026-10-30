# subscriptions/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q
from decimal import Decimal


class Plan(models.Model):
    code = models.SlugField(max_length=30, unique=True)  # "free", "basic", "premium"
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)  # RN-E2-05 / RN-E2-06
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PlanVersion(models.Model):
    """Condiciones contratables de un plan. Nunca se edita: cambiar precio o
    capacidad = crear una versión nueva (RN-E2-07 / RN-E2-08)."""

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="versions")
    name = models.CharField(max_length=100, blank=True)
    version_number = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="GTQ")
    capacity_bytes = models.BigIntegerField()
    duration_days = models.PositiveIntegerField(null=True, blank=True)  # null = sin vencimiento (Gratis)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.name:
            self.name = self.plan.name
        if self.pk:
            from django.core.exceptions import ValidationError
            original = type(self).objects.filter(pk=self.pk).first()
            fields = ('plan_id', 'name', 'version_number', 'currency', 'capacity_bytes', 'duration_days')
            changed = original and (Decimal(str(original.price)) != Decimal(str(self.price)) or
                any(getattr(original, field) != getattr(self, field) for field in fields))
            if changed:
                raise ValidationError('Las condiciones publicadas son inmutables. Crea otra versión del plan.')
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plan", "version_number"], name="unique_plan_version_number"),
            models.CheckConstraint(condition=Q(price__gte=0), name="plan_version_price_non_negative"),      # RN-E2-02
            models.CheckConstraint(condition=Q(capacity_bytes__gt=0), name="plan_version_capacity_positive"),  # RN-E2-03
            models.CheckConstraint(
                condition=Q(duration_days__isnull=True) | Q(duration_days__gt=0),
                name="plan_version_duration_positive",  # RN-E2-04
            ),
        ]

    def __str__(self):
        return f"{self.plan.code} v{self.version_number}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # null = sin vencimiento
    created_at = models.DateTimeField(auto_now_add=True)
    selected_plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, null=True, blank=True, related_name="selections")
    selected_at = models.DateTimeField(null=True, blank=True)
    selected_conditions = models.JSONField(default=dict)

    # R1 / R4: Día ancla del mes calendario en America/Guatemala y fin total de cobertura
    cycle_anchor_day = models.PositiveSmallIntegerField(null=True, blank=True)
    coverage_end = models.DateTimeField(null=True, blank=True)

    # R5: Próximo ciclo anticipado (máximo 1 ciclo siguiente ya pagado)
    next_cycle_starts_at = models.DateTimeField(null=True, blank=True)
    next_cycle_ends_at = models.DateTimeField(null=True, blank=True)
    next_cycle_plan_version = models.ForeignKey(
        PlanVersion, on_delete=models.PROTECT, null=True, blank=True, related_name="future_subscriptions"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user"], name="unique_subscription_identity_per_user"),
            # RN-E2-09: respaldo a nivel de base de datos.
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="active"),
                name="one_active_subscription_per_user",
            ),
        ]

    def __str__(self):
        return f"Subscription #{self.pk} - {self.user} - {self.plan_version} ({self.status})"


class ScheduledChange(models.Model):
    """R7 / Contrato 7.4: Cambio programado al terminar la cobertura pagada (downgrade o retorno a Gratis)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scheduled_change")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="scheduled_changes")
    target_plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="+")
    effective_at = models.DateTimeField()
    requires_payment = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ScheduledChange for {self.user} -> {self.target_plan_version.plan.code} at {self.effective_at}"


class Quote(models.Model):
    """Contrato 7.3: Cotización comercial temporal (vigencia 15 min)."""

    class Operation(models.TextChoices):
        CONTRACT = "contract", "Contract"
        RENEW = "renew", "Renew"
        CHANGE = "change", "Change"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        EXECUTED = "executed", "Executed"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quotes")
    operation = models.CharField(max_length=20, choices=Operation.choices)
    plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="quotes")
    currency = models.CharField(max_length=3, default="GTQ")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    requires_payment = models.BooleanField(default=True)
    lines = models.JSONField(default=list)
    effect = models.JSONField(default=dict)
    execution_context = models.JSONField(default=dict)
    plan_snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quote {self.id} ({self.operation}) - {self.user} - Total: {self.total} {self.currency}"


class SubscriptionPreference(models.Model):
    """Plan que el usuario marcó desde la landing. NO es cobertura."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plan_preference")
    plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)


class CoveragePeriod(models.Model):
    """R1/R9: evidencia de intervalos originales y sustituciones, con condiciones congeladas."""
    class State(models.TextChoices):
        VALID = "valid", "Válido"
        SUPERSEDED = "superseded", "Sustituido"

    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="coverage_history")
    plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="coverage_periods")
    conditions = models.JSONField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    cycle_starts_at = models.DateTimeField()
    cycle_ends_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.VALID)
    reason = models.CharField(max_length=24)
    payment = models.ForeignKey("payments.Payment", on_delete=models.PROTECT, null=True, blank=True, related_name="coverage_periods")
    supersedes = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="replacements")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__isnull=True) | Q(ends_at__gt=models.F("starts_at")), name="coverage_positive_interval"),
            models.UniqueConstraint(fields=["subscription"], condition=Q(state="valid", ends_at__isnull=True), name="one_open_coverage_period"),
        ]


class ScheduledOperation(models.Model):
    """Resultado recuperable de una confirmación sin cobro; cancelar no borra su evidencia."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="scheduled_operations")
    operation_key = models.UUIDField()
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, related_name="confirmation")
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "operation_key"], name="unique_scheduled_operation_per_user")]
