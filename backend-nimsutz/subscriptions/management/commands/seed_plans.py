# subscriptions/management/commands/seed_plans.py
from django.core.management.base import BaseCommand

from subscriptions.models import Plan, PlanVersion

MB = 1024 * 1024

PLANS = [
    {"code": "free", "name": "Gratis", "description": "Sin costo y sin vencimiento.",
     "price": "0.00", "capacity_bytes": 100 * MB, "duration_days": None},
    {"code": "basic", "name": "Básico", "description": "TODO",
     "price": "15.00", "capacity_bytes": 1024 * MB, "duration_days": 30},
    {"code": "premium", "name": "Premium", "description": "TODO",
     "price": "30.00", "capacity_bytes": 5120 * MB, "duration_days": 30},
]


class Command(BaseCommand):
    help = "Crea el catálogo inicial de planes. Seguro de correr varias veces."

    def handle(self, *args, **options):
        for data in PLANS:
            plan, created = Plan.objects.get_or_create(
                code=data["code"],
                defaults={"name": data["name"], "description": data["description"]},
            )
            # Solo crea la versión 1 si el plan no tiene ninguna; nunca pisa versiones existentes.
            if not plan.versions.exists():
                PlanVersion.objects.create(
                    plan=plan, version_number=1, price=data["price"], currency="GTQ",
                    capacity_bytes=data["capacity_bytes"], duration_days=data["duration_days"],
                )
            self.stdout.write(f"{'Creado' if created else 'Ya existe'}: {plan.code}")