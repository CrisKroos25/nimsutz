from accounts.administration import ActiveAdministrator

from .services import record_access_denied


class AuditedActiveAdministrator(ActiveAdministrator):
    """ActiveAdministrator que además audita el acceso denegado a quien ya inició sesión."""

    def has_permission(self, request, view):
        allowed = super().has_permission(request, view)
        if not allowed:
            record_access_denied(request)
        return allowed
