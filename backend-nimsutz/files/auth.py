from rest_framework.authentication import SessionAuthentication


class SimulatedUserAuthentication(SessionAuthentication):
    """Compatibility alias: a validated session is now required."""
