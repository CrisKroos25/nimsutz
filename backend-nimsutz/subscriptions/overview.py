# subscriptions/overview.py
from files.services import get_used_bytes

from . import services


def build_account_overview(user):
    subscription = services.get_active_subscription(user)
    capacity = subscription.plan_version.capacity_bytes if subscription else 0
    used = get_used_bytes(user)
    return {
        "coverage": services.subscription_payload(subscription) if subscription else None,
        "usage": {
            "used_bytes": used,
            "capacity_bytes": capacity,
            "available_bytes": max(capacity - used, 0),
        },
        "destination": services.resolve_destination(user),
    }