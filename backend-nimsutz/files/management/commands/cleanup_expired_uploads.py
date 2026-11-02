# files/management/commands/cleanup_expired_uploads.py
from django.core.management.base import BaseCommand

from files import storage_sync
from files.deletion import purge_account_objects


class Command(BaseCommand):
    help = "Libera reservas de cuota vencidas y reintenta el borrado de objetos pendientes."

    def handle(self, *args, **options):
        released = storage_sync.release_expired_reservations()
        purged, pending = storage_sync.purge_pending_objects()
        account_objects = purge_account_objects()
        self.stdout.write(
            f"Reservas liberadas: {released}. Objetos borrados: {purged}. Pendientes: {pending}. "
            f"Tareas de cuentas completadas: {account_objects}."
        )