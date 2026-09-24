import os
import boto3
from botocore.client import Config
from .models import Archivo

class MinIOService:
    @staticmethod
    def get_client():
        return boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )

    @staticmethod
    def generar_url_firmada_carga(clave_objeto, tipo_mime):
        s3_client = MinIOService.get_client()
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'nimsutz-files')
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': clave_objeto, 'ContentType': tipo_mime},
            ExpiresIn=900
        )
        # La URL firmada usa el hostname interno de Docker (minio:9000).
        # La reemplazamos por el endpoint público para que el navegador pueda acceder.
        internal = os.getenv('MINIO_ENDPOINT', 'http://minio:9000')
        public   = os.getenv('MINIO_PUBLIC_ENDPOINT', 'http://localhost:9000')
        return url.replace(internal, public)

    @staticmethod
    def generar_url_firmada_descarga(clave_objeto):
        s3_client = MinIOService.get_client()
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'nimsutz-files')
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': clave_objeto},
            ExpiresIn=900
        )
        # Misma corrección para las URLs de descarga
        internal = os.getenv('MINIO_ENDPOINT', 'http://minio:9000')
        public   = os.getenv('MINIO_PUBLIC_ENDPOINT', 'http://localhost:9000')
        return url.replace(internal, public)

    @staticmethod
    def eliminar_objeto_fisico(clave_objeto):
        """Elimina permanentemente el archivo guardado en el bucket de MinIO"""
        s3_client = MinIOService.get_client()
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'nimsutz-files')
        s3_client.delete_object(Bucket=bucket_name, Key=clave_objeto)


class TransferService:
    LIMITE_TAMANO_BYTES = 25 * 1024 * 1024  # 25 MB

    FORMATOS_PERMITIDOS = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'image/png',
        'image/jpeg'
    ]

    @staticmethod
    def validar_archivo(tamano_bytes, tipo_mime):
        if tamano_bytes > TransferService.LIMITE_TAMANO_BYTES:
            raise ValueError("El archivo supera el límite estricto de 25 MB.")
        if tipo_mime not in TransferService.FORMATOS_PERMITIDOS:
            raise ValueError("Formato no permitido. Solo se aceptan PDF, DOCX, TXT, PNG y JPG/JPEG.")

    @staticmethod
    def mover_a_papelera(archivo_id, usuario):
        archivo = Archivo.objects.get(id=archivo_id, usuario=usuario)
        archivo.estado = 'EN_PAPELERA'
        archivo.save()
        return archivo

    @staticmethod
    def restaurar_archivo(archivo_id, usuario):
        archivo = Archivo.objects.get(id=archivo_id, usuario=usuario, estado='EN_PAPELERA')
        # Si la carpeta contenedora fue eliminada previamente, se restaura en la raíz lógica
        if archivo.carpeta and not Archivo.objects.filter(id=archivo.carpeta_id).exists():
            archivo.carpeta = None
        archivo.estado = 'DISPONIBLE'
        archivo.save()
        return archivo

    @staticmethod
    def eliminar_definitivamente(archivo_id, usuario):
        """Elimina el registro de la BD y borra el contenido físico de MinIO, liberando cuota"""
        archivo = Archivo.objects.get(id=archivo_id, usuario=usuario, estado='EN_PAPELERA')
        # 1. Eliminar el objeto de MinIO
        MinIOService.eliminar_objeto_fisico(archivo.clave_objeto)
        # 2. Borrar metadatos en PostgreSQL
        archivo.delete()