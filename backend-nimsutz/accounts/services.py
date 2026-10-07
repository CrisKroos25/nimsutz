# accounts/services.py
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

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


from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings

# Placeholder for Miguel's service.
def send_verification_email(user_email: str, user_name: str, verification_link: str) -> None:
    """
    MOCK: Envía el correo con la plantilla de verificación.
    Miguel debe implementar esta función real.
    """
    print(f"MOCK EMAIL a {user_email}: Activa tu cuenta en {verification_link}")
    pass


class TokenError(Exception):
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def generate_verification_token(user: User) -> str:
    """
    Genera un token firmado con Timestamp.
    Firma el ID del usuario y su updated_at, de modo que cualquier cambio
    en el usuario (como un reenvío o su verificación) invalida tokens anteriores.
    """
    # Forzamos actualización de updated_at para invalidar cualquier token anterior.
    user.save(update_fields=["updated_at"])
    signer = TimestampSigner()
    payload = f"{user.pk}:{user.updated_at.timestamp()}"
    return signer.sign(payload)


def verify_email_with_token(token: str) -> User:
    """
    Valida el token y activa la cuenta del usuario.
    Retorna el usuario si tiene éxito, o lanza TokenError.
    """
    signer = TimestampSigner()
    try:
        # Expiración: 24 horas (86400 segundos)
        payload = signer.unsign(token, max_age=86400)
    except SignatureExpired:
        raise TokenError("expired_token", "El enlace de verificación ya expiró.")
    except BadSignature:
        raise TokenError("invalid_token", "El enlace de verificación es inválido.")

    try:
        user_id_str, timestamp_str = payload.split(":", 1)
        user = User.objects.get(pk=int(user_id_str))
    except (ValueError, User.DoesNotExist):
        raise TokenError("invalid_token", "El enlace de verificación es inválido.")

    # Verificar que el token corresponda al estado más reciente (invalidación de anteriores)
    if str(user.updated_at.timestamp()) != timestamp_str:
        # Si el usuario ya está activo, asumimos que usó otro token
        if user.account_status == User.AccountStatus.ACTIVE:
            raise TokenError("used_token", "Esta cuenta ya fue verificada.")
        else:
            raise TokenError("invalid_token", "El enlace expiró porque se solicitó uno nuevo.")

    # Validar que no estuviera ya suspendida
    if user.account_status == User.AccountStatus.SUSPENDED:
        raise TokenError("invalid_token", "La cuenta se encuentra suspendida.")

    # ¡Activar!
    user.account_status = User.AccountStatus.ACTIVE
    user.email_verified = True
    user.save(update_fields=["account_status", "email_verified", "updated_at"])
    
    return user


def resend_verification_email(email: str, base_url: str):
    """
    Reenvía el correo de verificación si la cuenta está pendiente.
    Invalida el enlace anterior.
    """
    normalized_email = email.strip().lower()
    try:
        user = User.objects.get(email=normalized_email)
    except User.DoesNotExist:
        # Por seguridad, no indicamos si el correo existe o no
        return

    # Si ya está activa o suspendida, no enviamos nada
    if user.account_status != User.AccountStatus.PENDING_VERIFICATION:
        return

    token = generate_verification_token(user)
    verification_link = f"{base_url}/verify-email?token={token}"
    
    send_verification_email(user.email, user.name, verification_link)
