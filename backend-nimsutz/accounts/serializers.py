from rest_framework import serializers
from .models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from .passwords import validate_new_password

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

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254)

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Este campo es requerido.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)

class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=True)
    email = serializers.EmailField(max_length=254, required=True)
    password = serializers.CharField(max_length=128, write_only=True, required=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(max_length=128, write_only=True, required=True, trim_whitespace=False)
    preferred_plan_version_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("El correo ingresado ya se encuentra en uso.")
        return value

    def validate(self, data):
        if data.get("password") != data.get("password_confirmation"):
            raise serializers.ValidationError({"password_confirmation": "Las contraseñas no coinciden."})
        
        password_user = User(name=data["name"], email=data["email"])
        try:
            validate_new_password(data["password"], password_user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
            
        return data

    def create(self, validated_data):
        create_data = validated_data.copy()
        create_data.pop("password_confirmation", None)
        create_data.pop("preferred_plan_version_id", None)
        user = User.objects.create_user(**create_data)
        return user