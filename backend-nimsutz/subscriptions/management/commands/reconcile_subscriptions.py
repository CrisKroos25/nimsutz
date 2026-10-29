# subscriptions/management/commands/reconcile_subscriptions.py
"""
R8 / Contrato 7.10:
Comando periódico de reconciliación de suscripciones (ejecutado cada minuto).
Procesa suscripciones vencidas de forma idempotente:
- Si tienen siguiente ciclo pagado (next_cycle), avanza al siguiente ciclo.
- Si tienen un cambio programado (ScheduledChange), aplica la bajada o retorno a Gratis.
- Si no tienen ciclo futuro ni cambio, retorna automáticamente a Gratis (conservando archivos).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import Subscription
from subscriptions.services import resolve_effective_subscription


class Command(BaseCommand):
    help = "Reconcilia suscripciones vencidas, aplica ciclos futuros, cambios programados y retorno a Gratis."

    def handle(self, *args, **options):
        now = timezone.now()
        # Buscar suscripciones activas cuya fecha de expiración ya haya pasado
        expired_subs = (
            Subscription.objects.select_related("user")
            .filter(status=Subscription.Status.ACTIVE, expires_at__isnull=False, expires_at__lte=now)
        )

        reconciled_count = 0
        for sub in expired_subs:
            resolved = resolve_effective_subscription(sub.user, at=now)
            reconciled_count += 1
            plan_name = resolved.plan_version.plan.name if resolved else "Sin cobertura"
            self.stdout.write(
                f"Suscripción de {sub.user.email} reconciliada: {plan_name} (expires: {resolved.expires_at if resolved else None})"
            )

        self.stdout.write(self.style.SUCCESS(f"Reconciliación completada. Total procesadas: {reconciled_count}"))

