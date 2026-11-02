"""
Configuración de Django. Todo lo que depende del entorno sale de variables.
Dev y producción usan este mismo archivo; solo cambian las variables.
"""
from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None, *, required=False):
    """Lee una variable de entorno. Si es obligatoria y falta, falla al arrancar."""
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise ImproperlyConfigured(f"Falta la variable de entorno obligatoria: {name}")
    return value


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# --- Núcleo -----------------------------------------------------------------------

SECRET_KEY = env("SECRET_KEY", required=True)
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1")

# Origen público del front (Vercel, o localhost en dev). Se usa en enlaces de correo.
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Orígenes desde los que el navegador puede enviar peticiones con CSRF.
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
)

# Render (y Vercel) terminan TLS antes de Django: hay que indicarle que la petición fue HTTPS.
if env_bool("USE_HTTPS", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600


# --- Aplicaciones -----------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'accounts',
    'files',
    'subscriptions',
    'payments',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.EnforceActiveAccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
AUTH_USER_MODEL = "accounts.User"


# --- Base de datos ----------------------------------------------------------------
# Local: DB_* en el .env de compose. Producción: se puede usar DATABASE_URL
# (Neon o Render la entregan completa), y solo cambia la variable.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env("DB_NAME", required=True),
        'USER': env("DB_USER", required=True),
        'PASSWORD': env("DB_PASSWORD", required=True),
        'HOST': env("DB_HOST", required=True),
        'PORT': env("DB_PORT", "5432"),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'sslmode': env("DB_SSLMODE", "prefer")},
    }
}


# --- Almacenamiento de archivos ----------------------------------------------------
# Mismo backend S3 para MinIO local, Cloudflare R2 o AWS S3. Solo cambian las variables.

STORAGE_BACKEND_CLASS = env("STORAGE_BACKEND_CLASS", "files.storage.s3_compatible.S3CompatibleStorageBackend")

STORAGE_BACKEND_CONFIG = {
    "bucket_name": env("STORAGE_BUCKET_NAME", required=True),
    "access_key": env("STORAGE_ACCESS_KEY", required=True),
    "secret_key": env("STORAGE_SECRET_KEY", required=True),
    # Interno: lo usa el servidor (head, delete). Público: va en las URLs firmadas.
    "internal_endpoint_url": env("STORAGE_ENDPOINT_URL", required=True),
    "public_endpoint_url": env("STORAGE_PUBLIC_ENDPOINT_URL", ""),
    "region_name": env("STORAGE_REGION", "us-east-1"),  # R2 usa "auto"
}

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # RN-E3-17
ALLOWED_CONTENT_TYPES = [               # RN-E3-18
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]

RESERVATION_TTL_MINUTES = int(env("RESERVATION_TTL_MINUTES", "10"))
PAID_PLANS_ENABLED = env_bool("PAID_PLANS_ENABLED", default=False)


# --- API y autenticación -----------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'user_attributes': ('name', 'email')},
    },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internacionalización y archivos estáticos -------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# --- Correo ------------------------------------------------------------------------
# Sin EMAIL_HOST el correo sale por consola (útil en dev). Con EMAIL_HOST, por SMTP.

_smtp_host = env("EMAIL_HOST", "").strip()

if _smtp_host:
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'OPTIONS': {
                'host': _smtp_host,
                'port': int(env("EMAIL_PORT", "587")),
                'username': env("EMAIL_HOST_USER", ""),
                'password': env("EMAIL_HOST_PASSWORD", ""),
                'use_tls': env_bool("EMAIL_USE_TLS", default=True),
                'timeout': int(env("EMAIL_TIMEOUT", "10")),
            },
        },
    }
else:
    MAILERS = {
        'default': {'BACKEND': 'django.core.mail.backends.console.EmailBackend'},
    }

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@nimsutz.local")
PASSWORD_RESET_TOKEN_TTL_MINUTES = int(env("PASSWORD_RESET_TOKEN_TTL_MINUTES", "30"))
EMAIL_VERIFICATION_TOKEN_TTL_MINUTES = int(env("EMAIL_VERIFICATION_TOKEN_TTL_MINUTES", "1440"))


# --- CORS --------------------------------------------------------------------------
# Con el rewrite de Vercel el navegador no hace peticiones cross-origin al backend.
# En dev, el front de Vite sí, y por eso se mantiene la lista.

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ALLOW_CREDENTIALS = True


# --- Pagos -------------------------------------------------------------------------

PAYMENTS_IDEMPOTENCY_SECRET = env("PAYMENTS_IDEMPOTENCY_SECRET", "")
CRON_TOKEN = env("CRON_TOKEN", "")