class PaymentError(Exception):
    def __init__(self, code, detail, status=409):
        self.code = code
        self.detail = detail
        self.status = status
        super().__init__(detail)

    def as_body(self):
        return {"code": self.code, "detail": self.detail, "field_errors": {}}
