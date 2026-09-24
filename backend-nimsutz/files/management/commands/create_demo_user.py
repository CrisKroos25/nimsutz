from getpass import getpass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Create the configured simulated user for local development."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.SIMULATED_AUTH_ENABLED:
            raise CommandError("Este comando requiere desarrollo y usuario simulado.")

        email = options["email"].strip().lower()
        try:
            validate_email(email)
        except ValidationError as error:
            raise CommandError("El correo no es válido.") from error

        user_model = get_user_model()
        user_id = settings.SIMULATED_USER_ID
        existing = user_model.objects.filter(pk=user_id).first()
        if existing:
            if existing.email.lower() != email:
                raise CommandError("El ID configurado pertenece a otra cuenta.")
            self.stdout.write("La cuenta ya existe. No se modificó su contraseña.")
            return

        if user_model.objects.filter(email__iexact=email).exists():
            raise CommandError("El correo ya existe con otro ID.")
        if user_model.objects.filter(username=email).exists():
            raise CommandError("El nombre de usuario ya está ocupado.")

        password = getpass("Contraseña de prueba: ")
        confirmation = getpass("Repite la contraseña: ")
        if not password or password != confirmation:
            raise CommandError("Las contraseñas deben coincidir y no estar vacías.")

        with transaction.atomic():
            user = user_model.objects.create_user(
                pk=user_id,
                username=email,
                email=email,
                password=password,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
            # El ID explícito no avanza la secuencia de PostgreSQL.
            with connection.cursor() as cursor:
                for statement in connection.ops.sequence_reset_sql(
                    no_style(), [user_model]
                ):
                    cursor.execute(statement)

        self.stdout.write(self.style.SUCCESS(
            f"Cuenta de prueba creada: {user.email} (ID {user.pk})."
        ))
