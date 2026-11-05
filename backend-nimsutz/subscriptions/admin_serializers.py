"""
Serializadores REST para la administración de planes y catálogo versionado (M19 - Rodrigo).
"""

from rest_framework import serializers


class AdminPlanVersionSerializer(serializers.Serializer):
    """Representación de una versión individual de plan."""

    id = serializers.IntegerField(read_only=True)
    version_number = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    price = serializers.CharField(read_only=True)
    capacity_bytes = serializers.IntegerField(read_only=True)
    billing_period = serializers.CharField(read_only=True, allow_null=True)
    currency = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)


class AdminPlanSerializer(serializers.Serializer):
    """Representación de un plan en la lista de catálogo administrativo."""

    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    active = serializers.BooleanField(read_only=True)
    current_version = AdminPlanVersionSerializer(read_only=True, allow_null=True)
    versions_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class PublishPlanVersionInputSerializer(serializers.Serializer):
    """Entrada para publicar una nueva versión con concurrencia optimista."""

    base_version_id = serializers.IntegerField(
        required=True,
        help_text="ID de la versión base sobre la cual se redactó la nueva versión.",
    )
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Nombre comercial para la versión.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Descripción detallada de la oferta.",
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        help_text="Precio en Quetzales (0.00 para Gratis).",
    )
    capacity_bytes = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Capacidad de almacenamiento en bytes (mayor a cero).",
    )
    billing_period = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Periodicidad ('calendar_month' o null para Gratis).",
    )
