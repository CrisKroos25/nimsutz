# subscriptions/urls.py
from django.urls import path
from . import views

plan_urlpatterns = [
    path("", views.PlanListView.as_view()),
]

subscription_urlpatterns = [
    path("preference/", views.PreferenceView.as_view()),
    path("current/", views.CurrentSubscriptionView.as_view()),
    path("activate-free/", views.ActivateFreeView.as_view()),
    path("quotes/", views.QuoteListCreateView.as_view()),
    path("quotes/<uuid:quote_id>/", views.QuoteDetailView.as_view()),
    path("quotes/<uuid:quote_id>/confirm/", views.QuoteConfirmView.as_view()),
    path("scheduled-change/", views.ScheduledChangeView.as_view()),
]

account_urlpatterns = [
    path("overview/", views.AccountOverviewView.as_view()),
]
