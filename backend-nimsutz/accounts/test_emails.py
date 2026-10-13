import json
import smtplib
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings

from . import services
from .emails import EmailDeliveryError, send_verification_email

LINK = "http://localhost:5173/verify-email?token=abc"


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

    def test_provider_failure_raises_specific_error_and_is_logged(self):
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
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

    def test_register_sends_real_email_with_verification_link(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["email_sent"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["nuevo@example.test"])
        self.assertIn("/verify-email?token=", mail.outbox[0].body)

    def test_register_survives_provider_failure_and_reports_it(self):
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
            response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["email_sent"])
        self.assertTrue(get_user_model().objects.filter(email="nuevo@example.test").exists())

    def test_resend_sends_email_to_pending_account(self):
        self.register()
        mail.outbox.clear()
        response = self.client.post(
            "/api/auth/resend-verification/",
            data=json.dumps({"email": "nuevo@example.test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_survives_provider_failure_with_generic_answer(self):
        self.register()
        with mock.patch("accounts.emails.send_mail", side_effect=smtplib.SMTPException("caido")):
            response = self.client.post(
                "/api/auth/resend-verification/",
                data=json.dumps({"email": "nuevo@example.test"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)

    def test_resend_unknown_email_sends_nothing(self):
        response = self.client.post(
            "/api/auth/resend-verification/",
            data=json.dumps({"email": "nadie@example.test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
