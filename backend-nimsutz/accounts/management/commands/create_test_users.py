from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea usuarios de prueba: dos clientes y un administrador (solo DEBUG)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando solo corre en desarrollo.")

        User = get_user_model()

        # Clientes de prueba
        clients = [
            ("ana@nimsutz.local", "Ana Prueba"),
            ("beto@nimsutz.local", "Beto Prueba"),
        ]

        for email, name in clients:
            if User.objects.filter(email__iexact=email).exists():
                self.stdout.write(f"Ya existe: {email}")
                continue

            User.objects.create_user(
                email=email,
                password="test-password-123",
                name=name,
                account_status=User.AccountStatus.ACTIVE,
                email_verified=True,
            )

            self.stdout.write(
                self.style.SUCCESS(f"Cliente creado: {email}")
            )

        # Administrador de prueba
        admin_email = "admin@nimsutz.local"
        admin_name = "Admin Prueba"

        if User.objects.filter(email__iexact=admin_email).exists():
            self.stdout.write(f"Ya existe: {admin_email}")
        else:
            User.objects.create_superuser(
                email=admin_email,
                password="admin-password-123",
                name=admin_name,
            )

            self.stdout.write(
                self.style.SUCCESS(f"Administrador creado: {admin_email}")
            )