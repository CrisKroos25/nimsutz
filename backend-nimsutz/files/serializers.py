# files/serializers.py
from rest_framework import serializers
from .models import Folder, File


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "parent", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        return value

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = [
            "id", "folder", "original_name", "content_type",
            "size_bytes", "status", "created_at", "updated_at",
        ]
        read_only_fields = fields


class RequestUploadSerializer(serializers.Serializer):
    folder = serializers.PrimaryKeyRelatedField(queryset=Folder.objects.all())
    original_name = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=100)
    size_bytes = serializers.IntegerField(min_value=1)


class RestoreFileSerializer(serializers.Serializer):
    new_name = serializers.CharField(max_length=255, required=False, allow_blank=False)