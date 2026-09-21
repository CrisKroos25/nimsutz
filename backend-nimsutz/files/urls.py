# files/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("folders/", views.FolderListCreateView.as_view()),
    path("folders/<int:pk>/", views.FolderDetailView.as_view()),

    path("files/", views.FileListView.as_view()),
    path("files/request-upload/", views.FileRequestUploadView.as_view()),
    path("files/<int:pk>/confirm-upload/", views.FileConfirmUploadView.as_view()),
    path("files/<int:pk>/request-download/", views.FileRequestDownloadView.as_view()),
]