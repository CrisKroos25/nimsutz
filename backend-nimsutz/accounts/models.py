# accounts/models.py
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El correo es obligatorio.")
        email = self.normalize_email(email).lower()  # RN-E1-02: comparación normalizada
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        # RN-E1-01 / RN-E1-22: toda cuenta creada por este método es Cliente
        # pendiente de verificación. Esta es la ÚNICA vía que debe usar el
        # endpoint público de registro.
        extra_fields.setdefault("role", User.Role.CLIENTE)
        extra_fields.setdefault("account_status", User.AccountStatus.PENDING_VERIFICATION)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        # Única vía para crear un Administrador — nunca desde el registro público.
        extra_fields.setdefault("role", User.Role.ADMINISTRADOR)
        extra_fields.setdefault("account_status", User.AccountStatus.ACTIVE)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None   # el correo reemplaza al username como identificador
    first_name = None # redundante con `name`, se elimina
    last_name = None

    class Role(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        ADMINISTRADOR = "administrador", "Administrador"

    class AccountStatus(models.TextChoices):
        PENDING_VERIFICATION = "pendiente_verificacion", "Pendiente de verificación"
        ACTIVE = "activa", "Activa"
        SUSPENDED = "suspendida", "Suspendida"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENTE)
    account_status = models.CharField(
        max_length=30,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING_VERIFICATION,
    )
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def can_use_private_features(self):
        # RN-E1-05 / RN-E1-11 / RN-E1-12: verificado Y activo (no pendiente, no suspendido)
        return self.email_verified and self.account_status == self.AccountStatus.ACTIVE