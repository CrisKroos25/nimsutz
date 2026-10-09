from django.contrib import admin
from django.urls import path, include
from accounts.urls import auth_urlpatterns, admin_urlpatterns
from subscriptions.urls import plan_urlpatterns, subscription_urlpatterns, account_urlpatterns

urlpatterns = [
    path('api/', include('files.urls')),    
    path("api/subscriptions/", include(subscription_urlpatterns)),
    path("api/auth/", include(auth_urlpatterns)),
    path("api/admin/", include(admin_urlpatterns)),
]
