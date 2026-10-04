import json

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST


def session_data(request):
    user = request.user
    return {
        "user": {"id": user.pk, "email": user.email} if user.is_authenticated else None,
        "csrfToken": get_token(request),
    }


@never_cache
@require_GET
def session_view(request):
    return JsonResponse(session_data(request))


@never_cache
@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
        email, password = data.get("email"), data.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            raise ValueError
        if not email.strip() or not password or len(email) > 254 or len(password) > 128:
            raise ValueError
    except (ValueError, AttributeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Ingresa un correo y una contraseña válidos."}, status=400)
    user = get_user_model().objects.filter(pk=settings.SIMULATED_USER_ID).first()
    authenticated = None
    if settings.SIMULATED_AUTH_ENABLED and user and user.email.casefold() == email.strip().casefold():
        authenticated = authenticate(request, username=user.get_username(), password=password)
    if authenticated is None or authenticated.is_staff or authenticated.is_superuser:
        return JsonResponse({"detail": "Correo o contraseña incorrectos."}, status=401)
    login(request, authenticated)
    return JsonResponse(session_data(request))


@never_cache
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse(session_data(request))
