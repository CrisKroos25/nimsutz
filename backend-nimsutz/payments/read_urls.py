# payments/read_urls.py
from django.urls import path

from .read_views import PaymentHistoryDetailView, PaymentHistoryView

read_urlpatterns = [
    path("", PaymentHistoryView.as_view()),
    path("<int:payment_id>/", PaymentHistoryDetailView.as_view()),
]
