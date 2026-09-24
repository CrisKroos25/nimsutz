from django.urls import path
from .views import (
    SolicitarCargaView,
    ConfirmarCargaView,
    MoverAPapeleraView,
    SolicitarDescargaView,
    ListarPapeleraView,
    RestaurarArchivoView,
    EliminarDefinitivoView
)

urlpatterns = [
    # Transferencias y archivos
    path('solicitar-carga/', SolicitarCargaView.as_view(), name='solicitar-carga'),
    path('<int:archivo_id>/confirmar/', ConfirmarCargaView.as_view(), name='confirmar-carga'),
    path('<int:archivo_id>/descargar/', SolicitarDescargaView.as_view(), name='solicitar-descarga'),
    path('<int:archivo_id>/', MoverAPapeleraView.as_view(), name='mover-a-papelera'),

    # Papelera
    path('papelera/', ListarPapeleraView.as_view(), name='listar-papelera'),
    path('papelera/<int:archivo_id>/restaurar/', RestaurarArchivoView.as_view(), name='restaurar-archivo'),
    path('papelera/<int:archivo_id>/eliminar-definitivo/', EliminarDefinitivoView.as_view(), name='eliminar-definitivo'),
]