# accounts/services.py
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import PasswordResetToken

from .models import User


class AuthenticationError(Exception):
    """Credenciales incorrectas o cuenta sin permiso para iniciar sesión (401)."""


def authenticate_user(*, email, password):
    normalized_email = email.strip().lower()

    # authenticate() ya aplica RN-E1-10 (no revela cuál dato falló) y
    # RN-E1-12/E1-13 (is_active=False bloquea el login) vía ModelBackend.
    user = authenticate(username=normalized_email, password=password)
    if user is None:
        raise AuthenticationError("Credenciales inválidas.")

    # RN-E1-11: pendiente no puede usar funcionalidades privadas.
    # RN-E1-12: suspendida no puede iniciar sesión.
    # Separado de is_active a propósito: is_active es el interruptor técnico
    # de Django, account_status es tu estado de negocio real.
    if user.account_status != User.AccountStatus.ACTIVE:
        raise AuthenticationError("La cuenta no puede iniciar sesión en este momento.")

    return user

class AuthorizationError(Exception):
    """El usuario está autenticado pero no tiene permiso para esta acción (403)."""


def suspend_account(*, actor, target):
    if actor.role != User.Role.ADMINISTRADOR:
        raise AuthorizationError("Solo un administrador puede suspender cuentas.")  # RN-E4-03

    if target.role == User.Role.ADMINISTRADOR:
        raise ValidationError("No se puede suspender a otro administrador.")

    if target.pk == actor.pk:
        raise ValidationError("No puedes suspender tu propia cuenta.")

    if target.account_status == User.AccountStatus.SUSPENDED:
        return target  # idempotente, mismo criterio que trash_file en files

    target.account_status = User.AccountStatus.SUSPENDED
    target.save(update_fields=["account_status", "updated_at"])
    # RN-E4-05: no se tocan archivos, carpetas, suscripciones ni pagos del usuario.
    return target


def reactivate_account(*, actor, target):
    if actor.role != User.Role.ADMINISTRADOR:
        raise AuthorizationError("Solo un administrador puede reactivar cuentas.")  # RN-E4-04

    if target.account_status != User.AccountStatus.SUSPENDED:
        raise ValidationError("Solo una cuenta suspendida puede reactivarse.")

    target.account_status = User.AccountStatus.ACTIVE
    target.save(update_fields=["account_status", "updated_at"])
    return target

def request_password_reset(*, email):
    normalized_email = email.strip().lower()

    try:
        user = User.objects.get(email__iexact=normalized_email)
    except User.DoesNotExist:
        # RN propia: no revelamos si el correo existe o no (mismo criterio
        # que authenticate_user con las credenciales de login).
        return None

    token = PasswordResetToken.issue(user)
    return token


def confirm_password_reset(*, token, new_password):
    try:
        reset_token = PasswordResetToken.objects.select_related("user").get(token=token)
    except PasswordResetToken.DoesNotExist:
        raise AuthenticationError("El enlace de recuperación no es válido.")

    if not reset_token.is_valid:
        raise AuthenticationError("El enlace de recuperación venció o ya fue usado.")

    user = reset_token.user
    validate_password(new_password, user)  # lanza ValidationError si es débil
    user.set_password(new_password)
    user.save(update_fields=["password"])
    reset_token.mark_used()
    return user