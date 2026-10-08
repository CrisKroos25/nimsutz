from django.conf import settings
from django.core.mail import send_mail


def _send(*, to_email, subject, body):
    # Punto único de envío: la verificación de correo de Rodrigo puede
    # reutilizar esta función sin tocar las reglas de token de recuperación.
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )


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