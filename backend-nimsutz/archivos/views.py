import uuid
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from .services import TransferService, MinIOService
from .models import Archivo
from .serializers import ArchivoSerializer

User = get_user_model()

class SolicitarCargaView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        tamano_bytes = request.data.get('tamano_bytes', 0)
        tipo_mime = request.data.get('tipo_mime', '')
        nombre = request.data.get('nombre', '')
        id_carpeta = request.data.get('id_carpeta', None)

        try:
            # 1. Validaciones de tamaño y tipo de archivo (25 MB)
            TransferService.validar_archivo(tamano_bytes, tipo_mime)
            
            # 2. Asignar un usuario para la prueba local en la BD
            user = request.user if request.user.is_authenticated else User.objects.first()
            if not user:
                # Si la BD no tiene ningún usuario registrado, crea uno auxiliar rápido para pruebas
                user = User.objects.create_user(username='test_dev', email='test@nimsutz.com')

            # 3. Clave única de objeto en MinIO (UUID evita colisiones con el mismo nombre de archivo)
            clave_objeto = f"users/{user.id}/{uuid.uuid4().hex}/{nombre}"
            
            # 4. Generar URL firmada con boto3
            upload_url = MinIOService.generar_url_firmada_carga(clave_objeto, tipo_mime)

            # 5. Registrar metadatos en estado PROCESANDO
            archivo = Archivo.objects.create(
                nombre=nombre,
                tamano_bytes=tamano_bytes,
                tipo_mime=tipo_mime,
                clave_objeto=clave_objeto,
                estado='PROCESANDO',
                usuario=user,
                carpeta_id=id_carpeta
            )

            return Response({
                "id": archivo.id,
                "upload_url": upload_url,
                "clave_objeto": clave_objeto
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Imprime el detalle del error en la terminal de Docker para fácil depuración
            print(f"Error interno en SolicitarCargaView: {str(e)}")
            return Response({"error": f"Error interno del servidor: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmarCargaView(APIView):
    """Recibe el archivo_id por URL: POST /api/archivos/<id>/confirmar/"""
    permission_classes = [AllowAny]

    def post(self, request, archivo_id):
        try:
            archivo = Archivo.objects.get(id=archivo_id)
            archivo.estado = 'DISPONIBLE'
            archivo.save()
            return Response({"mensaje": "Archivo disponible en el sistema."}, status=status.HTTP_200_OK)
        except Archivo.DoesNotExist:
            return Response({"error": "No se encontró la reserva del archivo."}, status=status.HTTP_404_NOT_FOUND)


class MoverAPapeleraView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, archivo_id):
        try:
            archivo = Archivo.objects.get(id=archivo_id)
            archivo.estado = 'EN_PAPELERA'
            archivo.save()
            return Response({"mensaje": f"Archivo '{archivo.nombre}' movido a la papelera."}, status=status.HTTP_200_OK)
        except Archivo.DoesNotExist:
            return Response({"error": "Archivo no encontrado."}, status=status.HTTP_404_NOT_FOUND)


class SolicitarDescargaView(APIView):
    """GET /api/archivos/<id>/descargar/"""
    permission_classes = [AllowAny]

    def get(self, request, archivo_id):
        try:
            archivo = Archivo.objects.get(id=archivo_id, estado='DISPONIBLE')
            download_url = MinIOService.generar_url_firmada_descarga(archivo.clave_objeto)
            return Response({"download_url": download_url}, status=status.HTTP_200_OK)
        except Archivo.DoesNotExist:
            return Response({"error": "Archivo no encontrado o no disponible."}, status=status.HTTP_404_NOT_FOUND)


class ListarPapeleraView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        archivos = Archivo.objects.filter(estado='EN_PAPELERA')
        serializer = ArchivoSerializer(archivos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RestaurarArchivoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, archivo_id):
        try:
            archivo = Archivo.objects.get(id=archivo_id, estado='EN_PAPELERA')
            archivo.estado = 'DISPONIBLE'
            archivo.save()
            return Response({"mensaje": f"Archivo '{archivo.nombre}' restaurado correctamente."}, status=status.HTTP_200_OK)
        except Archivo.DoesNotExist:
            return Response({"error": "Archivo no encontrado en la papelera."}, status=status.HTTP_404_NOT_FOUND)


class EliminarDefinitivoView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, archivo_id):
        try:
            archivo = Archivo.objects.get(id=archivo_id, estado='EN_PAPELERA')
            MinIOService.eliminar_objeto_fisico(archivo.clave_objeto)
            archivo.delete()
            return Response({"mensaje": "Archivo eliminado permanentemente de MinIO y PostgreSQL."}, status=status.HTTP_200_OK)
        except Archivo.DoesNotExist:
            return Response({"error": "El archivo no existe en la papelera."}, status=status.HTTP_404_NOT_FOUND)