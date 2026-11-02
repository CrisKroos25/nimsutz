# files/serializers.py
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Folder, File
from .validators import normalize_folder_name


class FolderNameField(serializers.CharField):
    def to_internal_value(self, data):
        try:
            return normalize_folder_name(data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error


class FolderRenameSerializer(serializers.Serializer):
    name = FolderNameField()


class FolderSerializer(serializers.ModelSerializer):
    name = FolderNameField()

    class Meta:
        model = Folder
        fields = ["id", "parent", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = [
            "id", "folder", "original_name", "content_type",
            "size_bytes", "status", "created_at", "updated_at",
        ]
        read_only_fields = fields


class RequestUploadSerializer(serializers.Serializer):
    folder = serializers.PrimaryKeyRelatedField(
            queryset=Folder.objects.all(), allow_null=True, default=None
    )    
    original_name = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=100)
    size_bytes = serializers.IntegerField(min_value=1)


class RestoreFileSerializer(serializers.Serializer):
    new_name = serializers.CharField(max_length=255, required=False, allow_blank=False)