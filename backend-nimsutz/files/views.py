# files/views.py
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import File, Folder
from .serializers import FileSerializer, FolderSerializer, RequestUploadSerializer, RestoreFileSerializer


# ---------- Folders ----------

class FolderListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # futuro: E1 agrega IsAccountActive aquí (global, vía settings, no hace falta tocar esto)

    def get(self, request):
        queryset = Folder.objects.filter(owner=request.user)
        parent_param = request.query_params.get("parent")
        if parent_param == "root":
            queryset = queryset.filter(parent__isnull=True)
        elif parent_param is not None:
            queryset = queryset.filter(parent_id=parent_param)
        return Response(FolderSerializer(queryset, many=True).data)

    def post(self, request):
        # futuro: E2 agrega aquí HasActiveSubscription (solo en escritura, RN-E2-18)
        serializer = FolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            folder = services.create_folder(
                owner=request.user,
                parent=serializer.validated_data.get("parent"),
                name=serializer.validated_data["name"],
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(FolderSerializer(folder).data, status=status.HTTP_201_CREATED)


class FolderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        folder = get_object_or_404(Folder, pk=pk, owner=request.user)
        new_name = request.data.get("name")
        if not new_name:
            raise DRFValidationError({"name": "Este campo es requerido."})

        try:
            folder = services.rename_folder(folder=folder, new_name=new_name)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(FolderSerializer(folder).data)

    def delete(self, request, pk):
        folder = get_object_or_404(Folder, pk=pk, owner=request.user)
        try:
            services.delete_folder(folder=folder)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- Files ----------

class FileListView(generics.ListAPIView):
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = File.objects.filter(owner=self.request.user)
        folder_id = self.request.query_params.get("folder")
        status_param = self.request.query_params.get("status", File.Status.AVAILABLE)
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)
        return queryset.filter(status=status_param)


class FileRequestUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # futuro: E2 agrega aquí HasActiveSubscription (es escritura/consumo de cuota)

    def post(self, request):
        serializer = RequestUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            file, upload_url = services.request_upload(
                owner=request.user, **serializer.validated_data
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(
            {"file": FileSerializer(file).data, "upload_url": upload_url},
            status=status.HTTP_201_CREATED,
        )


class FileConfirmUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        file = get_object_or_404(File, pk=pk, owner=request.user)
        try:
            file = services.confirm_upload(file=file, owner=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(FileSerializer(file).data)


class FileRequestDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # descarga: E2 NO bloquea esto ni vencida la suscripción (RN-E2-18), por eso
    # este permission_classes se queda solo con IsAuthenticated, a propósito.

    def get(self, request, pk):
        file = get_object_or_404(File, pk=pk, owner=request.user)
        try:
            url = services.request_download(file=file, owner=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response({"download_url": url})


# ---------- Recycle Bin and deletion ----------

class FileTrashView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        file = get_object_or_404(File, pk=pk, owner=request.user)
        try:
            file = services.trash_file(file=file, owner=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(FileSerializer(file).data)


class FileRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # futuro: E2 agrega aquí HasActiveSubscription (restaurar cuenta como escritura, RN-E2-18)

    def post(self, request, pk):
        file = get_object_or_404(File, pk=pk, owner=request.user)
        serializer = RestoreFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            file = services.restore_file(
                file=file,
                owner=request.user,
                new_name=serializer.validated_data.get("new_name"),
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(FileSerializer(file).data)


class FilePermanentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        file = get_object_or_404(File, pk=pk, owner=request.user)
        try:
            services.permanently_delete_file(file=file, owner=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})
        return Response(status=status.HTTP_204_NO_CONTENT)