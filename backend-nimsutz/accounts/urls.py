from django.urls import path
from . import views

auth_urlpatterns = [
    path("session/", views.SessionView.as_view()),
    path("login/", views.LoginView.as_view()),
    path("logout/", views.LogoutView.as_view()),
    path("password-reset/", views.PasswordResetRequestView.as_view()),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view()),
]

admin_urlpatterns = [
    path("users/<int:pk>/suspend/", views.SuspendUserView.as_view()),
    path("users/<int:pk>/reactivate/", views.ReactivateUserView.as_view()),
]