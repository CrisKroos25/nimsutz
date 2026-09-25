from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),   # login, sesión, logout
    path('api/', include('files.urls')),           # explorador A + transferencias B
    path('api/archivos/', include('archivos.urls')),  # app propia de B (coexiste)
]
