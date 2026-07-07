from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from core_api.permissions import EsAdminJuridicoOSuperadmin, PermisoProceso, PermisoSubrecursoDeProceso
from core_api.serializers import (
    AccionFuturaSerializer,
    CategoriaSerializer,
    DocumentoProcesoSerializer,
    EstadoProcesoSerializer,
    HistorialEstadoSerializer,
    JuzgadoSerializer,
    ParteSerializer,
    ProcesoDetalleSerializer,
    ProcesoListaSerializer,
    TipoProcesoSerializer,
    UsuarioResumenSerializer,
)
from procesos.models import AccionFutura, DocumentoProceso, HistorialEstado, Proceso
from usuarios.models import es_admin_juridico, es_abogado


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [EsAdminJuridicoOSuperadmin]


class TipoProcesoViewSet(viewsets.ModelViewSet):
    queryset = TipoProceso.objects.select_related("categoria").all()
    serializer_class = TipoProcesoSerializer
    permission_classes = [EsAdminJuridicoOSuperadmin]
    filterset_fields = ["categoria"]


class JuzgadoViewSet(viewsets.ModelViewSet):
    queryset = Juzgado.objects.all()
    serializer_class = JuzgadoSerializer
    permission_classes = [EsAdminJuridicoOSuperadmin]


class EstadoProcesoViewSet(viewsets.ModelViewSet):
    queryset = EstadoProceso.objects.all()
    serializer_class = EstadoProcesoSerializer
    permission_classes = [EsAdminJuridicoOSuperadmin]


class ParteViewSet(viewsets.ModelViewSet):
    queryset = Parte.objects.all()
    serializer_class = ParteSerializer
    permission_classes = [EsAdminJuridicoOSuperadmin]
    filterset_fields = ["tipo_persona"]
    search_fields = ["nombre", "nro_documento"]


class AbogadoViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista de abogados, para poblar selects de asignación."""

    queryset = User.objects.filter(perfil__rol="ABOGADO", is_active=True).order_by("first_name", "last_name")
    serializer_class = UsuarioResumenSerializer


class ProcesoViewSet(viewsets.ModelViewSet):
    queryset = Proceso.objects.select_related(
        "categoria", "tipo_proceso", "juzgado", "estado_actual", "abogado_responsable"
    ).prefetch_related("partes__parte", "historial", "acciones_futuras", "documentos", "detalle_contrato")
    permission_classes = [PermisoProceso]
    filterset_fields = ["categoria", "estado_actual", "juzgado", "abogado_responsable", "activo"]
    search_fields = ["nro_correlativo", "nurej"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcesoListaSerializer
        return ProcesoDetalleSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if es_abogado(user) and not es_admin_juridico(user):
            serializer.save(abogado_responsable=user)
        else:
            serializer.save()


class HistorialEstadoViewSet(viewsets.ModelViewSet):
    queryset = HistorialEstado.objects.select_related("proceso", "usuario", "estado_anterior", "estado_nuevo")
    serializer_class = HistorialEstadoSerializer
    permission_classes = [PermisoSubrecursoDeProceso]
    filterset_fields = ["proceso"]

    def perform_create(self, serializer):
        proceso = serializer.validated_data["proceso"]
        user = self.request.user
        if es_abogado(user) and not es_admin_juridico(user) and proceso.abogado_responsable_id != user.id:
            raise PermissionDenied("Solo el abogado responsable del proceso puede añadir historial.")
        historial = serializer.save(usuario=user)
        proceso.estado_actual = historial.estado_nuevo
        proceso.save(update_fields=["estado_actual", "actualizado_en"])


class AccionFuturaViewSet(viewsets.ModelViewSet):
    queryset = AccionFutura.objects.select_related("proceso", "responsable")
    serializer_class = AccionFuturaSerializer
    permission_classes = [PermisoSubrecursoDeProceso]
    filterset_fields = ["proceso", "completada"]


class DocumentoProcesoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoProceso.objects.select_related("proceso", "subido_por")
    serializer_class = DocumentoProcesoSerializer
    permission_classes = [PermisoSubrecursoDeProceso]
    filterset_fields = ["proceso"]

    def perform_create(self, serializer):
        serializer.save(subido_por=self.request.user)