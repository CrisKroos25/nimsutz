"""Borrado explícito de pagos propios tras retirar las referencias de cobertura."""

from .models import CardMovement, Payment, PaymentDetail


def erase_customer_payments(user):
    CardMovement.objects.filter(payment__owner=user).delete()
    PaymentDetail.objects.filter(payment__owner=user).delete()
    Payment.objects.filter(owner=user).delete()
    # Las tarjetas del simulador son compartidas; no se borran ni se repone saldo.
