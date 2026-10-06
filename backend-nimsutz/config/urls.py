from django.contrib import admin
from django.urls import path, include
from accounts.urls import auth_urlpatterns, admin_urlpatterns

urlpatterns = [
    path('api/', include('files.urls')),        
    path("api/auth/", include(auth_urlpatterns)),
    path("api/admin/", include(admin_urlpatterns)),
]
