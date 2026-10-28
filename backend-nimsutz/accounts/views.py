import logging

from django.contrib.auth import login as django_login, logout as django_logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import Serializer, CharField, EmailField
from subscriptions.services import resolve_destination, set_preference
from subscriptions.errors import SubscriptionError

from . import services, emails
from .models import User

logger = logging.getLogger(__name__)

from .serializers import (
    LoginSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
)


def _auth_payload(request, user):
    return {
        "user": UserSerializer(user).data if user else None,
        "destination": resolve_destination(user) if user else None,
        "csrfToken": get_token(request),
    }

def _email_delivery_failed_response():
    return Response(
        {
            "code": "email_delivery_failed",
            "detail": "No pudimos enviar el correo. Intenta de nuevo en un momento.",
            "field_errors": {},
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )

class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        return Response(_auth_payload(request, user))


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = services.authenticate_user(**serializer.validated_data)
        except services.AuthenticationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        django_login(request, user)
        return Response(_auth_payload(request, user))


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    def post(self, request):
        django_logout(request)
        return Response({"user": None, "csrfToken": get_token(request)})


class SuspendUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        try:
            target = services.suspend_account(actor=request.user, target=target)
        except services.AuthorizationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(UserSerializer(target).data)


class ReactivateUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        try:
            target = services.reactivate_account(actor=request.user, target=target)
        except services.AuthorizationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(UserSerializer(target).data)

@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = services.request_password_reset(**serializer.validated_data)
        if token is not None:
            try:
                emails.send_password_reset_email(user=token.user, token=token.token)
            except emails.EmailDeliveryError:
                logger.warning(
                    "No se pudo enviar el correo de recuperacion del usuario %s.", token.user_id
                )
                return _email_delivery_failed_response()

        return Response(
            {"detail": "Si el correo existe, se envio un enlace de recuperacion."}
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            services.confirm_password_reset(**serializer.validated_data)
        except services.AuthenticationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except DjangoValidationError as e:
            raise DRFValidationError({"new_password": e.messages})

        return Response({"detail": "Contraseña actualizada correctamente."})

@method_decorator(transaction.non_atomic_requests, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "validation_error",
                "detail": "Datos inválidos",
                "field_errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            # Dos registros simultáneos con el mismo correo: gana el primero.
            return Response({
                "code": "validation_error",
                "detail": "Datos inválidos",
                "field_errors": {"email": ["El correo ingresado ya se encuentra en uso."]},
            }, status=status.HTTP_400_BAD_REQUEST)

        # Guardar preferencia de plan usando el servicio de Cristian
        preferred_plan_version_id = serializer.validated_data.get("preferred_plan_version_id")
        preference_saved = False
        if preferred_plan_version_id:
            try:
                set_preference(user=user, plan_version_id=preferred_plan_version_id)
                preference_saved = True
            except SubscriptionError as exc:
                logger.warning(
                    "No se pudo guardar la preferencia para el usuario %s (plan_version_id=%s): %s",
                    user.pk,
                    preferred_plan_version_id,
                    exc,
                )
            except Exception:
                logger.exception(
                    "Error inesperado al guardar la preferencia del usuario %s.", user.pk
                )

        token = services.generate_verification_token(user)
        verification_link = services.build_verification_link(token)

        try:
            services.send_verification_email(user.email, user.name, verification_link)
        except emails.EmailDeliveryError:
            logger.warning("No se pudo enviar el correo de verificacion del usuario %s.", user.pk)
            # La cuenta ya está confirmada y queda pendiente: el usuario puede reintentar el envío.
            return Response(
                {
                    "code": "email_delivery_failed",
                    "detail": "Tu cuenta quedó creada, pero no pudimos enviar el correo. Reintenta el envío.",
                    "field_errors": {},
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_data = UserSerializer(user).data
        response_data["status"] = "pending_verification"
        response_data["email_sent"] = True
        response_data["preference_saved"] = preference_saved

        return Response(response_data, status=status.HTTP_201_CREATED)

class VerifyEmailSerializer(Serializer):
    token = CharField(required=True)

class ResendVerificationSerializer(Serializer):
    email = EmailField(required=True)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            services.verify_email_with_token(serializer.validated_data["token"])
        except services.TokenError as e:
            return Response({"code": e.code, "detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Correo verificado exitosamente."})

class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            services.resend_verification_email(
                email=serializer.validated_data["email"]
            )
        except services.ResendCooldownError as exc:
            return Response(
                {
                    "code": "resend_cooldown",
                    "detail": str(exc),
                    "field_errors": {},
                    "retry_after": exc.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(exc.retry_after)},
            )
        except emails.EmailDeliveryError:
            logger.warning("No se pudo reenviar el correo de verificacion.")
            return _email_delivery_failed_response()

        return Response({
            "detail": "Si el correo está registrado y pendiente, se ha enviado un nuevo enlace."
        })