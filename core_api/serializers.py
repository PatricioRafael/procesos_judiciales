from django.contrib.auth.models import User
from rest_framework import serializers

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from procesos.models import (
    AccionFutura,
    DetalleContrato,
    DocumentoProceso,
    HistorialEstado,
    Proceso,
    ProcesoParte,
)


class UsuarioResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "slug", "orden"]


class TipoProcesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoProceso
        fields = ["id", "nombre", "categoria"]


class JuzgadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Juzgado
        fields = ["id", "nombre", "tipo"]


class EstadoProcesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoProceso
        fields = ["id", "nombre", "orden", "es_final"]


class ParteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parte
        fields = ["id", "nombre", "tipo_persona", "nro_documento"]


class ProcesoParteSerializer(serializers.ModelSerializer):
    parte_nombre = serializers.CharField(source="parte.nombre", read_only=True)

    class Meta:
        model = ProcesoParte
        fields = ["id", "parte", "parte_nombre", "rol"]


class DetalleContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleContrato
        fields = ["proyecto", "nro_contrato", "fecha_contrato", "motivo_demanda"]


class HistorialEstadoSerializer(serializers.ModelSerializer):
    usuario = UsuarioResumenSerializer(read_only=True)
    estado_nuevo_nombre = serializers.CharField(source="estado_nuevo.nombre", read_only=True)

    class Meta:
        model = HistorialEstado
        fields = [
            "id", "proceso", "estado_anterior", "estado_nuevo", "estado_nuevo_nombre",
            "usuario", "fecha_modificacion", "observacion", "creado_en",
        ]
        read_only_fields = ["usuario", "creado_en"]


class AccionFuturaSerializer(serializers.ModelSerializer):
    responsable = UsuarioResumenSerializer(read_only=True)
    responsable_id = serializers.PrimaryKeyRelatedField(
        source="responsable", queryset=User.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = AccionFutura
        fields = ["id", "proceso", "descripcion", "fecha_limite", "completada", "responsable", "responsable_id", "creado_en"]


class DocumentoProcesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoProceso
        fields = ["id", "proceso", "archivo", "descripcion", "subido_por", "fecha_subida"]
        read_only_fields = ["subido_por", "fecha_subida"]


class ProcesoListaSerializer(serializers.ModelSerializer):
    """Versión ligera para listados/tablas."""

    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    juzgado_nombre = serializers.CharField(source="juzgado.nombre", read_only=True)
    estado_nombre = serializers.CharField(source="estado_actual.nombre", read_only=True)
    abogado_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Proceso
        fields = [
            "id", "nro_correlativo", "nurej", "categoria", "categoria_nombre",
            "juzgado_nombre", "estado_nombre", "abogado_nombre", "abogado_referencia",
            "activo", "actualizado_en",
        ]

    def get_abogado_nombre(self, obj):
        if not obj.abogado_responsable:
            return None
        return obj.abogado_responsable.get_full_name() or obj.abogado_responsable.username


class ProcesoDetalleSerializer(serializers.ModelSerializer):
    """Versión completa: partes, historial, acciones y detalle de contrato."""

    partes = ProcesoParteSerializer(many=True, read_only=True)
    historial = HistorialEstadoSerializer(many=True, read_only=True)
    acciones_futuras = AccionFuturaSerializer(many=True, read_only=True)
    documentos = DocumentoProcesoSerializer(many=True, read_only=True)
    detalle_contrato = DetalleContratoSerializer(required=False)
    abogado_responsable = UsuarioResumenSerializer(read_only=True)
    abogado_responsable_id = serializers.PrimaryKeyRelatedField(
        source="abogado_responsable", queryset=User.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Proceso
        fields = [
            "id", "nro_correlativo", "nurej", "categoria", "tipo_proceso", "juzgado",
            "estado_actual", "abogado_responsable", "abogado_responsable_id", "abogado_referencia",
            "fecha_registro", "activo", "creado_en", "actualizado_en",
            "partes", "historial", "acciones_futuras", "documentos", "detalle_contrato",
        ]
        read_only_fields = ["creado_en", "actualizado_en"]

    def update(self, instance, validated_data):
        detalle_data = validated_data.pop("detalle_contrato", None)
        instance = super().update(instance, validated_data)
        if detalle_data is not None:
            DetalleContrato.objects.update_or_create(proceso=instance, defaults=detalle_data)
        return instance

    def create(self, validated_data):
        detalle_data = validated_data.pop("detalle_contrato", None)
        proceso = super().create(validated_data)
        if detalle_data:
            DetalleContrato.objects.create(proceso=proceso, **detalle_data)
        return proceso