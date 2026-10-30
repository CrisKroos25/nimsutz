"""Ejecutor local de la reconciliación; no aplica migraciones ni cobra automáticamente."""

import time
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Ejecuta reconcile_subscriptions cada 60 segundos; --once permite una comprobación."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=60)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        interval = options["interval"]
        if interval < 1:
            raise CommandError("El intervalo debe ser positivo.")
        while True:
            if not connection.in_atomic_block:
                close_old_connections()
            try:
                executor = MigrationExecutor(connection)
                pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
                if pending:
                    if options["once"]:
                        raise CommandError(
                            "Aplica las migraciones antes de reconciliar."
                        )
                    self.stdout.write(
                        "Migraciones pendientes; la reconciliación esperará su aplicación."
                    )
                else:
                    call_command("reconcile_subscriptions", stdout=self.stdout)
            except OperationalError:
                if options["once"]:
                    raise CommandError("La base de datos no está disponible.") from None
                self.stderr.write(
                    "Base de datos no disponible; se reintentará la reconciliación."
                )
            if options["once"]:
                return
            time.sleep(interval)
