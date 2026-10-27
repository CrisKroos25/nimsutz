from django.urls import path
from .views import CheckoutView, OperationResultView, PaymentResultView

urlpatterns = [
    path("checkout/", CheckoutView.as_view()),
    path("operations/<uuid:operation_key>/", OperationResultView.as_view()),
    path("results/<int:payment_id>/", PaymentResultView.as_view()),
]
