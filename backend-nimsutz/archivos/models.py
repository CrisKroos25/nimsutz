from django.db import models
from django.conf import settings

class Carpeta(models.Model):
    nombre = models.CharField(max_length=255)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    carpeta_padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subcarpetas')
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Archivo(models.Model):
    ESTADOS = [
        ('PROCESANDO', 'Procesando'),
        ('DISPONIBLE', 'Disponible'),
        ('ERROR', 'Error'),
        ('EN_PAPELERA', 'En Papelera'),
    ]

    nombre = models.CharField(max_length=255)
    tamano_bytes = models.BigIntegerField()
    tipo_mime = models.CharField(max_length=100)
    clave_objeto = models.CharField(max_length=500, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROCESANDO')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    carpeta = models.ForeignKey(Carpeta, null=True, blank=True, on_delete=models.CASCADE, related_name='archivos')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre