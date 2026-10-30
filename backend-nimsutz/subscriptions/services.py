"""Entradas compatibles del módulo comercial; las reglas se organizan por responsabilidad."""

from .catalog import get_current_version, is_contractable, list_catalog, version_payload
from .coverage import (
    activate_free,
    get_active_subscription,
    resolve_effective_subscription,
)
from .payloads import (
    get_allowed_actions,
    next_cycle_payload,
    pending_selection_payload,
    quote_payload,
    scheduled_change_payload,
    subscription_payload,
)
from .preferences import get_preference, resolve_destination, set_preference
from .quotations import (
    apply_approved_quote,
    get_quote,
    prepare_quote,
    validate_quote_for_execution,
)
from .scheduled import cancel_scheduled_change, confirm_scheduled_quote

FREE_PLAN_CODE = "free"
BASIC_PLAN_CODE = "basic"
PREMIUM_PLAN_CODE = "premium"
