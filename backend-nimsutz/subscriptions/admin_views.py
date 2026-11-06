"""
Vistas REST para el módulo de administración de catálogo y versiones de planes (M19 - Rodrigo).
Cumple con los contratos HTTP definidos en la guía del hito 100%.
"""

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .admin_serializers import (
    AdminPlanSerializer,
    AdminPlanVersionSerializer,
    PublishPlanVersionInputSerializer,
)
from .errors import SubscriptionError
from .permissions import IsAdminUserRole, check_admin_role_and_active


class AdminCatalogPagination(PageNumberPagination):
    """Paginación estándar para listados administrativos con límite configurable."""
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminCatalogBaseView(APIView):
    """
    Clase base para todos los endpoints administrativos del catálogo de planes.
    Garantiza autenticación, rol de administrador, cuenta activa y manejo consistente de errores.
    """
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        check_admin_role_and_active(request.user)

    def handle_exception(self, exc):
        if isinstance(exc, SubscriptionError):
            return Response(exc.as_body(), status=exc.http_status)
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated, PermissionDenied)):
            code = "csrf_failed" if "csrf" in str(exc).lower() else "forbidden"
            detail = getattr(exc, "detail", str(exc))
            return Response({"code": code, "detail": str(detail), "field_errors": {}}, status=403)
        return super().handle_exception(exc)


class AdminPlanListView(AdminCatalogBaseView):
    """
    GET /api/administration/plans/?active=&page=1
    Lista planes del sistema con su versión vigente y total de versiones publicadas.
    """

    def get(self, request):
        active_param = request.query_params.get("active")
        active_filter = None
        if active_param is not None:
            val = active_param.strip().lower()
            if val in ("true", "1"):
                active_filter = True
            elif val in ("false", "0"):
                active_filter = False

        plans = services.list_admin_plans(active=active_filter)

        paginator = AdminCatalogPagination()
        page = paginator.paginate_queryset(plans, request)
        serializer = AdminPlanSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminPlanVersionView(AdminCatalogBaseView):
    """
    GET  /api/administration/plans/<int:plan_id>/versions/?page=1
         Historial completo de versiones de un plan.
    POST /api/administration/plans/<int:plan_id>/versions/
         Publica una nueva versión inmutable con concurrencia optimista (base_version_id).
    """

    def get(self, request, plan_id: int):
        data = services.list_plan_versions(plan_id=plan_id)
        paginator = AdminCatalogPagination()
        page = paginator.paginate_queryset(data["versions"], request)
        serializer = AdminPlanVersionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, plan_id: int):
        serializer = PublishPlanVersionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "code": "invalid_request",
                    "detail": "Datos de entrada inválidos para la nueva versión.",
                    "field_errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        result = services.publish_plan_version(
            admin_user=request.user,
            plan_id=plan_id,
            base_version_id=validated["base_version_id"],
            name=validated.get("name", ""),
            description=validated.get("description", ""),
            price=validated["price"],
            capacity_bytes=validated["capacity_bytes"],
            billing_period=validated.get("billing_period"),
        )

        return Response(result, status=status.HTTP_201_CREATED)


class AdminPlanDeactivateView(AdminCatalogBaseView):
    """
    POST /api/administration/plans/<int:plan_id>/deactivate/
    Desactiva la disponibilidad de un plan para nuevas contrataciones.
    """

    def post(self, request, plan_id: int):
        result = services.deactivate_plan(
            admin_user=request.user,
            plan_id=plan_id,
        )
        return Response(result, status=status.HTTP_200_OK)

