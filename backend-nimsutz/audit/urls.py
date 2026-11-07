from django.urls import path

from .views import AuditEventDetailView, AuditEventListView

administration_urlpatterns = [
    path("audit/", AuditEventListView.as_view()),
    path("audit/<int:event_id>/", AuditEventDetailView.as_view()),
]
