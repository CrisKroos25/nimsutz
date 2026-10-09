# subscriptions/errors.py
class SubscriptionError(Exception):
    STATUS_BY_CODE = {
        "invalid_request": 400,
        "account_not_eligible": 403,
        "plan_unavailable": 409,
        "plan_without_version": 409,
        "plan_conditions_changed": 409,
        "coverage_conflict": 409,
    }

    def __init__(self, code, message, field_errors=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_errors = field_errors or {}

    @property
    def http_status(self):
        return self.STATUS_BY_CODE.get(self.code, 400)

    def as_body(self):
        return {"detail": self.message, "code": self.code, "field_errors": self.field_errors}