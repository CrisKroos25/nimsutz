# accounts/services.py
from django.contrib.auth import SESSION_KEY, authenticate
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from .emails import send_verification_email
from .models import PasswordResetToken
from .passwords import validate_new_password

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
    if not user.can_use_private_features:
        raise AuthenticationError("La cuenta no puede iniciar sesión en este momento.")

    return user

class AuthorizationError(Exception):
    """El usuario está autenticado pero no tiene permiso para esta acción (403)."""

def invalidate_user_sessions(user, *, include_expired=False):
    """Invalida sesiones; el borrado definitivo incluye también las vencidas."""
    target = str(user.pk)
    sessions = Session.objects.all()
    if not include_expired:
        sessions = sessions.filter(expire_date__gt=timezone.now())
    invalidated = 0
    for session in sessions.iterator():
        if session.get_decoded().get(SESSION_KEY) == target:
            session.delete()
            invalidated += 1
    return invalidated


def _require_active_administrator(actor):
    if (actor.role != User.Role.ADMINISTRADOR or not actor.email_verified
            or actor.account_status != User.AccountStatus.ACTIVE):
        raise AuthorizationError("Se requiere un administrador activo y verificado.")


def _record_account_event(*, actor, action, target, result, metadata):
    """Integra con el servicio persistente de Miguel cuando su módulo esté disponible."""
    try:
        from audit.services import record_event
    except ImportError as exc:
        raise RuntimeError("El servicio persistente de auditoría aún no está integrado.") from exc
    return record_event(actor=actor, action=action, entity_type="client",
                        entity_id=str(target.pk), result=result, metadata=metadata)

def suspend_account(*, actor, target):
    with transaction.atomic():
        actor = User.objects.select_for_update().get(pk=actor.pk)
        _require_active_administrator(actor)
        target = User.objects.select_for_update().get(pk=target.pk)
        if target.role == User.Role.ADMINISTRADOR:
            raise ValidationError("No se puede suspender a otro administrador.")
        if target.pk == actor.pk:
            raise ValidationError("No puedes suspender tu propia cuenta.")
        previous_status = target.account_status
        if previous_status == User.AccountStatus.SUSPENDED:
            _record_account_event(actor=actor, action="client.suspended", target=target,
                                  result="no_change", metadata={"previous_status": previous_status,
                                                                "new_status": previous_status})
            target._admin_changed = False
            target._sessions_invalidated = False
            return target
        target.account_status = User.AccountStatus.SUSPENDED
        target.save(update_fields=["account_status", "updated_at"])
        invalidated = invalidate_user_sessions(target)
        _record_account_event(actor=actor, action="client.suspended", target=target, result="success",
                              metadata={"previous_status": previous_status,
                                        "new_status": target.account_status})
        target._admin_changed = True
        target._sessions_invalidated = invalidated > 0
    # RN-E4-05: no se tocan archivos, carpetas, suscripciones ni pagos del usuario.
    return target


def reactivate_account(*, actor, target):
    with transaction.atomic():
        actor = User.objects.select_for_update().get(pk=actor.pk)
        _require_active_administrator(actor)
        target = User.objects.select_for_update().get(pk=target.pk)
        if target.role == User.Role.ADMINISTRADOR:
            raise ValidationError("No se puede reactivar a otro administrador.")
        previous_status = target.account_status
        if previous_status != User.AccountStatus.SUSPENDED:
            raise ValidationError("Solo una cuenta suspendida puede reactivarse.")
        # Una cuenta suspendida antes de verificar su correo vuelve a pendiente
        target.account_status = (
            User.AccountStatus.ACTIVE
            if target.email_verified
            else User.AccountStatus.PENDING_VERIFICATION
        )
        target.save(update_fields=["account_status", "updated_at"])
        invalidated = invalidate_user_sessions(target)
        _record_account_event(actor=actor, action="client.reactivated", target=target, result="success",
                              metadata={"previous_status": previous_status,
                                        "new_status": target.account_status})
        target._admin_changed = True
        target._sessions_invalidated = invalidated > 0
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
    with transaction.atomic():
        try:
            reset_token = (
                PasswordResetToken.objects.select_for_update()
                .select_related("user")
                .get(token=token)
            )
        except PasswordResetToken.DoesNotExist:
            raise AuthenticationError("El enlace de recuperación no es válido.")

        if not reset_token.is_valid:
            raise AuthenticationError("El enlace de recuperación venció o ya fue usado.")

        user = reset_token.user
        validate_new_password(new_password, user)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        reset_token.mark_used()
    return user


class TokenError(Exception):
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(detail)

RESEND_COOLDOWN_SECONDS = 60
class ResendCooldownError(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(f"Espera {retry_after} segundos para reenviar el correo.")


def build_verification_link(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"


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
    signer = TimestampSigner()  # usa el mismo signer que generate_verification_token
    try:
        max_age = settings.EMAIL_VERIFICATION_TOKEN_TTL_MINUTES * 60
        payload = signer.unsign(token, max_age=max_age)
    except SignatureExpired:
        raise TokenError("expired_token", "El enlace de verificación ya expiró.")
    except BadSignature:
        raise TokenError("invalid_token", "El enlace de verificación es inválido.")

    try:
        user_id_str, timestamp_str = payload.split(":", 1)
        user_id = int(user_id_str)
    except ValueError:
        raise TokenError("invalid_token", "El enlace de verificación es inválido.")

    with transaction.atomic():
        user = User.objects.select_for_update().filter(pk=user_id).first()
        if user is None:
            raise TokenError("invalid_token", "El enlace de verificación es inválido.")

        if str(user.updated_at.timestamp()) != timestamp_str:
            if user.account_status == User.AccountStatus.ACTIVE:
                raise TokenError("used_token", "Esta cuenta ya fue verificada.")
            raise TokenError("invalid_token", "El enlace expiró porque se solicitó uno nuevo.")

        if user.account_status == User.AccountStatus.SUSPENDED:
            raise TokenError("invalid_token", "La cuenta se encuentra suspendida.")

        user.account_status = User.AccountStatus.ACTIVE
        user.email_verified = True
        user.save(update_fields=["account_status", "email_verified", "updated_at"])

    return user


def resend_verification_email(email: str):
    """
    Reenvía el correo de verificación si la cuenta está pendiente.
    Invalida el enlace anterior. Lanza ResendCooldownError si es muy pronto.
    """
    normalized_email = email.strip().lower()

    with transaction.atomic():
        user = (
            User.objects.select_for_update()
            .filter(email__iexact=normalized_email)
            .first()
        )
        # Por seguridad no se distingue entre inexistente, activa o suspendida.
        if user is None or user.account_status != User.AccountStatus.PENDING_VERIFICATION:
            return

        # En una cuenta pendiente, updated_at solo cambia al generar un token.
        elapsed = (timezone.now() - user.updated_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            raise ResendCooldownError(int(RESEND_COOLDOWN_SECONDS - elapsed) + 1)

        token = generate_verification_token(user)

    # El envío va fuera del lock para no retener la fila durante el SMTP.
    send_verification_email(user.email, user.name, build_verification_link(token))
