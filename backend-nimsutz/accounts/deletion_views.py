"""Eliminar la cuenta autenticada requiere confirmación explícita y CSRF."""

from django.contrib.auth import logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .deletion import delete_own_account


class DeleteAccountSerializer(serializers.Serializer):
    confirm = serializers.JSONField()

    def validate(self, attrs):
        if set(self.initial_data) != {"confirm"} or attrs["confirm"] is not True:
            raise serializers.ValidationError(
                {"confirm": "Confirma la eliminación de tu cuenta."}
            )
        return attrs


@method_decorator(transaction.non_atomic_requests, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class DeleteOwnAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        confirmation = DeleteAccountSerializer(data=request.data)
        confirmation.is_valid(raise_exception=True)
        pending = delete_own_account(request.user)
        logout(request)
        return Response(
            {
                "user": None,
                "deletion_pending": pending,
                "detail": (
                    "Tu cuenta se eliminó. Estamos terminando de borrar tus archivos."
                    if pending
                    else "Tu cuenta y todos sus datos se eliminaron."
                ),
                "csrfToken": get_token(request),
            },
            status=202 if pending else 200,
        )
