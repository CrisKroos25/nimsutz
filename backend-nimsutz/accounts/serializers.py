from rest_framework import serializers
from .models import User

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Este campo es requerido.")
        return value

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "account_status", "email_verified"]
        read_only_fields = fields

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=True)
    email = serializers.EmailField(max_length=254, required=True)
    password = serializers.CharField(max_length=128, write_only=True, required=True)
    password_confirmation = serializers.CharField(max_length=128, write_only=True, required=True)
    preferred_plan_version_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("El correo ingresado ya se encuentra en uso.")
        return value

    def validate(self, data):
        if data.get("password") != data.get("password_confirmation"):
            raise serializers.ValidationError({"password_confirmation": "Las contraseñas no coinciden."})
        
        # Validación estricta de Django (8 caracteres, etc.)
        try:
            validate_password(data.get("password"))
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
            
        return data

    def create(self, validated_data):
        # preferred_plan_version_id is extracted but not passed to user creation yet
        # It will be handled in the view later or passed to Cristian's service.
        validated_data.pop("password_confirmation")
        validated_data.pop("preferred_plan_version_id", None)
        
        # user manager's create_user forces role Client and status Pending
        user = User.objects.create_user(**validated_data)
        return user