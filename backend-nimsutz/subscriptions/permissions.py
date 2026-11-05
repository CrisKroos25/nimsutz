"""
Permisos de acceso administrativo para el catálogo versionado (M19 - Rodrigo).
"""

from rest_framework.permissions import BasePermission
from accounts.models import User
from .errors import SubscriptionError


def check_admin_role_and_active(user) -> None:
    """Valida que el usuario tenga rol de administrador y cuenta activa."""
    if not user or not user.is_authenticated:
        raise SubscriptionError("forbidden", "Autenticación requerida para acceder al módulo administrativo.")

    role = getattr(user, "role", None)
    if role != User.Role.ADMINISTRADOR and role != "administrador":
        raise SubscriptionError("forbidden", "Acceso denegado. Se requiere rol de administrador.")

    account_status = getattr(user, "account_status", None)
    if account_status != User.AccountStatus.ACTIVE and account_status != "activa":
        raise SubscriptionError("forbidden", "La cuenta de administrador no se encuentra en estado activo.")

    if not getattr(user, "is_active", True):
        raise SubscriptionError("forbidden", "La cuenta de usuario está desactivada.")


class IsAdminUserRole(BasePermission):
    """
    DRF Permission class para asegurar rol de administrador verificado y activo.
    """
    message = "Acceso restringido a administradores autorizados."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", None)
        if role != User.Role.ADMINISTRADOR and role != "administrador":
            return False

        account_status = getattr(user, "account_status", None)
        if account_status != User.AccountStatus.ACTIVE and account_status != "activa":
            return False

        if not getattr(user, "is_active", True):
            return False

        return True
