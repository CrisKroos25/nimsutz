import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class TestCard(models.Model):
    """Datos exclusivamente ficticios; nunca se carga una tarjeta bancaria real."""
    number = models.CharField(max_length=16, unique=True)
    holder = models.CharField(max_length=120)
    security_code_hash = models.CharField(max_length=128)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    currency = models.CharField(max_length=3, default="GTQ")
    enabled = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(balance__gte=0), name="payment_card_nonnegative_balance"),
            models.CheckConstraint(condition=Q(expiry_month__gte=1, expiry_month__lte=12), name="payment_card_valid_month"),
        ]


class Payment(models.Model):
    class Status(models.TextChoices):
        APPROVED = "approved", "Aprobado"
        REJECTED = "rejected", "Rechazado"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    operation_key = models.UUIDField()
    request_digest = models.CharField(max_length=64)
    quote_id = models.UUIDField()
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices)
    reason_code = models.CharField(max_length=40, null=True, blank=True)
    operation = models.CharField(max_length=12)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    card_last4 = models.CharField(max_length=4, blank=True)
    plan_snapshot = models.JSONField()
    result_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "operation_key"], name="unique_payment_operation_per_user"),
            models.UniqueConstraint(fields=["owner", "quote_id"], condition=Q(status="approved"), name="one_approved_payment_per_quote"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="payment_nonnegative_amount"),
        ]


class PaymentDetail(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="lines")
    code = models.CharField(max_length=40)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)


class CardMovement(models.Model):
    card = models.ForeignKey(TestCard, on_delete=models.PROTECT, related_name="movements")
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="movement")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
