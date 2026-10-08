# accounts/views.py
from django.contrib.auth import login as django_login, logout as django_logout
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

from . import services, emails
from .models import User
from .serializers import (
    LoginSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)


class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_data = UserSerializer(request.user).data if request.user.is_authenticated else None
        return Response({"user": user_data, "csrfToken": get_token(request)})


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
        return Response({"user": UserSerializer(user).data, "csrfToken": get_token(request)})


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
                pass

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