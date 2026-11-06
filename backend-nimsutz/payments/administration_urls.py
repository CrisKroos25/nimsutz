from django.urls import path

from .administration import (
    AdministrationPaymentDetailView,
    AdministrationPaymentListView,
    MetricsView,
)

administration_urlpatterns = [
    path("metrics/", MetricsView.as_view()),
    path("payments/", AdministrationPaymentListView.as_view()),
    path("payments/<int:payment_id>/", AdministrationPaymentDetailView.as_view()),
]
