# accounts/middleware.py
from django.contrib.auth import logout as django_logout

from .models import User


class EnforceActiveAccountMiddleware:
    """
    RN-E1-13: una suspensión debe impedir operaciones de una sesión ya
    iniciada, no solo bloquear logins nuevos. Se revisa en cada request
    autenticado, después de que AuthenticationMiddleware ya resolvió
    request.user desde la cookie de sesión.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.account_status != User.AccountStatus.ACTIVE:
            django_logout(request)  # destruye la sesión; request.user pasa a AnonymousUser
        return self.get_response(request)