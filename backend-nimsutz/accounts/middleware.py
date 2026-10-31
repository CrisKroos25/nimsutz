# accounts/middleware.py
from django.contrib.auth import logout as django_logout


class EnforceActiveAccountMiddleware:
    """
    RN-E1-13: una suspensión debe impedir operaciones de una sesión ya
    iniciada, no solo bloquear logins nuevos. Se revisa en cada request
    autenticado, después de que AuthenticationMiddleware ya resolvió
    request.user desde la cookie de sesión.

    Usa can_use_private_features (verificada y activa) para que login,
    sesiones y permisos apliquen la misma regla.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.can_use_private_features:
            django_logout(request)  # destruye la sesión; request.user pasa a AnonymousUser
        return self.get_response(request)