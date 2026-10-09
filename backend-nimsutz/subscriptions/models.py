# subscriptions/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q


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
    version_number = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="GTQ")
    capacity_bytes = models.BigIntegerField()
    duration_days = models.PositiveIntegerField(null=True, blank=True)  # null = sin vencimiento (Gratis)
    created_at = models.DateTimeField(auto_now_add=True)

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
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)  # null = sin vencimiento
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # RN-E2-09: respaldo a nivel de base de datos. Aunque dos peticiones
            # simultáneas se salten la validación en Python, Postgres rechaza la segunda.
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="active"),
                name="one_active_subscription_per_user",
            ),
        ]


class SubscriptionPreference(models.Model):
    """Plan que el usuario marcó desde la landing. NO es cobertura."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plan_preference")
    plan_version = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)