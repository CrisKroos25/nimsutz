# files/auth.py
from rest_framework.authentication import BaseAuthentication
from django.conf import settings
from django.contrib.auth import get_user_model


class SimulatedUserAuthentication(BaseAuthentication):
    def authenticate(self, request):
        User = get_user_model()
        user = User.objects.get(pk=settings.SIMULATED_USER_ID)
        return (user, None)