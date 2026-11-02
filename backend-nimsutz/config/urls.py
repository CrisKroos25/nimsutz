from django.contrib import admin
from django.urls import path, include

from accounts.urls import auth_urlpatterns, admin_urlpatterns
from subscriptions.urls import plan_urlpatterns, subscription_urlpatterns, account_urlpatterns
from config.views import health, run_scheduled_tasks

urlpatterns = [
    path("health/", health, name="health"),
    path("api/internal/scheduled-tasks/", run_scheduled_tasks, name="scheduled-tasks"),
    path("api/payments/", include("payments.urls")),
    path("api/", include("files.urls")),
    path("api/plans/", include(plan_urlpatterns)),
    path("api/subscriptions/", include(subscription_urlpatterns)),
    path("api/account/", include(account_urlpatterns)),
    path("api/auth/", include(auth_urlpatterns)),
    path("api/admin/", include(admin_urlpatterns)),
]