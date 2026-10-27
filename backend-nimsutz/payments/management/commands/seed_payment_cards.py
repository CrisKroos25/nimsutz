from decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from payments.models import TestCard


class Command(BaseCommand):
    help = "Crea tarjetas ficticias sin restablecer saldos existentes (solo desarrollo/pruebas)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando solo se permite en un entorno de pruebas con DEBUG=True.")
        year = timezone.now().year
        scenarios = [
            ("9999000000000001", "Aprobable", "500.00", True, year + 2, "GTQ"),
            ("9999000000000002", "Sin saldo", "0.00", True, year + 2, "GTQ"),
            ("9999000000000003", "Deshabilitada", "500.00", False, year + 2, "GTQ"),
            ("9999000000000004", "Vencida", "500.00", True, year - 1, "GTQ"),
            ("9999000000000005", "Otra moneda", "500.00", True, year + 2, "USD"),
        ]
        for number, label, balance, enabled, expiry_year, currency in scenarios:
            _, created = TestCard.objects.get_or_create(number=number, defaults={
                "holder": "NIM SUTZ DEMO", "security_code_hash": make_password("123"),
                "expiry_month": 12, "expiry_year": expiry_year, "currency": currency,
                "enabled": enabled, "balance": Decimal(balance),
            })
            self.stdout.write(f"{label}: {'creada' if created else 'conservada'} (terminación {number[-4:]})")
