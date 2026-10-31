import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """El transporte de correo no pudo entregar un mensaje."""


def _mask_email(email):
    if not email or "@" not in email:
        return "<destinatario invalido>"
    domain = email.rsplit("@", 1)[1]
    return f"***@{domain}"


def _send(*, to_email, subject, body):
    # Punto único de envío: la verificación de correo de Rodrigo puede
    # reutilizar esta función sin tocar las reglas de token de recuperación.
    if not isinstance(to_email, str) or not to_email.strip():
        raise ValueError("El destinatario del correo es obligatorio.")

    try:
        sent_count = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except OSError as exc:
        logger.error(
            "Fallo el envio de correo a %s (error %s).",
            _mask_email(to_email),
            type(exc).__name__,
        )
        raise EmailDeliveryError("No se pudo entregar el correo.") from exc
    if sent_count != 1:
        logger.error("El transporte no acepto el correo para %s.", _mask_email(to_email))
        raise EmailDeliveryError("El transporte no acepto el correo.")


def send_password_reset_email(*, user, token):
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    minutes = settings.PASSWORD_RESET_TOKEN_TTL_MINUTES
    _send(
        to_email=user.email,
        subject="Recuperación de contraseña - Nim sutz'",
        body=(
            f"Hola {user.name},\n\n"
            "Recibimos una solicitud para restablecer tu contraseña.\n"
            f"Usa este enlace (válido por {minutes} minutos):\n\n"
            f"{link}\n\n"
            "Si no fuiste tú, ignora este mensaje."
        ),
    )

def send_verification_email(user_email: str = None, user_name: str = None, verification_link: str = None, *, to_email: str = None) -> None:
    """Envía la verificación o lanza ValueError/EmailDeliveryError."""
    target_email = to_email or user_email
    if not target_email:
        raise ValueError("Se requiere user_email o to_email para enviar la verificación.")
    minutes = settings.EMAIL_VERIFICATION_TOKEN_TTL_MINUTES
    _send(
        to_email=target_email,
        subject="Verifica tu correo - Nim sutz'",
        body=(
            f"Hola {user_name},\n\n"
            "Gracias por crear tu cuenta en Nim sutz'.\n"
            "Confirma tu correo con este enlace (tiene una vigencia limitada):\n\n"
            f"{verification_link}\n\n"
            f"Este enlace es válido por {minutes} minutos y solo puede utilizarse una vez.\n"
            "Si no creaste esta cuenta, ignora este mensaje."
        ),
    )
