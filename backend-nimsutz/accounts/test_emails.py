import json
import smtplib
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import services
from .emails import EmailDeliveryError, send_verification_email

LINK = "http://localhost:5173/verify-email?token=abc"


def after_cooldown():
    """Adelanta el reloj de Django 61 s para saltarse la espera del reenvío."""
    return mock.patch(
        "django.utils.timezone.now",
        return_value=timezone.now() + timedelta(seconds=61),
    )


class VerificationEmailTests(TestCase):
    def test_sends_message_with_link_name_and_configured_sender(self):
        with override_settings(DEFAULT_FROM_EMAIL="no-reply@nimsutz.test"):
            send_verification_email("ana@example.test", "Ana", LINK)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["ana@example.test"])
        self.assertEqual(message.from_email, "no-reply@nimsutz.test")
        self.assertIn("Verifica tu correo", message.subject)
        self.assertIn("Ana", message.body)
        self.assertIn(LINK, message.body)

    def test_verification_message_uses_configured_token_ttl(self):
        with override_settings(EMAIL_VERIFICATION_TOKEN_TTL_MINUTES=45):
            send_verification_email("ana@example.test", "Ana", LINK)
        self.assertIn("válido por 45 minutos", mail.outbox[0].body)

    def test_verification_requires_a_recipient(self):
        with self.assertRaisesRegex(ValueError, "user_email o to_email"):
            send_verification_email(user_name="Ana", verification_link=LINK)

    def test_provider_failure_raises_specific_error_and_is_logged(self):
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
            with self.assertLogs("accounts.emails", level="ERROR") as logs:
                with self.assertRaises(EmailDeliveryError):
                    send_verification_email("ana@example.test", "Ana", LINK)
        self.assertNotIn("ana@example.test", "\n".join(logs.output))

    def test_zero_delivered_messages_raise_delivery_error(self):
        with mock.patch("accounts.emails.send_mail", return_value=0):
            with self.assertLogs("accounts.emails", level="ERROR"):
                with self.assertRaises(EmailDeliveryError):
                    send_verification_email("ana@example.test", "Ana", LINK)

    def test_verification_does_not_use_recovery_tokens(self):
        send_verification_email("ana@example.test", "Ana", LINK)
        self.assertNotIn("reset-password", mail.outbox[0].body)


class VerificationEmailIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def register(self, email="nuevo@example.test"):
        data = {
            "name": "Nuevo", "email": email,
            "password": "Password123!", "password_confirmation": "Password123!",
        }
        return self.client.post(
            "/api/auth/register/", data=json.dumps(data), content_type="application/json"
        )

    def resend(self, email="nuevo@example.test", **extra):
        return self.client.post(
            "/api/auth/resend-verification/",
            data=json.dumps({"email": email}),
            content_type="application/json",
            **extra,
        )

    def test_register_sends_real_email_with_verification_link(self):
        with override_settings(FRONTEND_URL="https://app.example.test/"):
            response = self.client.post(
                "/api/auth/register/",
                data=json.dumps({
                    "name": "Nuevo",
                    "email": "nuevo@example.test",
                    "password": "Password123!",
                    "password_confirmation": "Password123!",
                }),
                content_type="application/json",
                HTTP_ORIGIN="http://localhost:5173",
            )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["email_sent"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["nuevo@example.test"])
        self.assertIn("https://app.example.test/verify-email?token=", mail.outbox[0].body)
        self.assertNotIn("localhost", mail.outbox[0].body)

    def test_register_reports_provider_failure_and_keeps_pending_account(self):
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
            response = self.register()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "email_delivery_failed")
        self.assertEqual(len(mail.outbox), 0)

        user = get_user_model().objects.get(email="nuevo@example.test")
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)

    def test_register_view_is_outside_request_wide_transactions(self):
        from accounts.views import RegisterView

        view = RegisterView.as_view()
        self.assertIn("default", view._non_atomic_requests)

    def test_resend_sends_email_to_pending_account(self):
        self.register()
        mail.outbox.clear()
        with override_settings(FRONTEND_URL="https://app.example.test/"):
            with after_cooldown():
                response = self.resend(HTTP_ORIGIN="http://localhost:5173")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://app.example.test/verify-email?token=", mail.outbox[0].body)
        self.assertNotIn("localhost", mail.outbox[0].body)

    def test_resend_right_after_register_returns_429(self):
        self.register()
        mail.outbox.clear()
        response = self.resend()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "resend_cooldown")
        self.assertGreater(response.json()["retry_after"], 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_reports_provider_failure(self):
        self.register()
        mail.outbox.clear()
        with after_cooldown():
            with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
                response = self.resend()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "email_delivery_failed")
        self.assertEqual(len(mail.outbox), 0)

        user = get_user_model().objects.get(email="nuevo@example.test")
        self.assertEqual(user.account_status, get_user_model().AccountStatus.PENDING_VERIFICATION)

    def test_resend_unknown_email_sends_nothing(self):
        response = self.resend(email="nadie@example.test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)