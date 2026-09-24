from rest_framework import serializers
from .models import Archivo, Carpeta

class CarpetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carpeta
        fields = ['id', 'nombre', 'carpeta_padre', 'creado_en']
        read_only_fields = ['id', 'creado_en']


class ArchivoSerializer(serializers.ModelSerializer):
    # Campo calculado para enviar el tamaño formateado al frontend si se requiere
    tamano_mb = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields = [
            'id', 
            'nombre', 
            'tamano_bytes', 
            'tamano_mb',
            'tipo_mime', 
            'clave_objeto', 
            'estado', 
            'carpeta', 
            'creado_en', 
            'actualizado_en'
        ]
        read_only_fields = ['id', 'clave_objeto', 'creado_en', 'actualizado_en']

    def get_tamano_mb(self, obj):
        # Transforma los bytes a Megabytes con 2 decimales para la UI
        return round(obj.tamano_bytes / (1024 * 1024), 2)