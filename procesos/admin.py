from django.contrib import admin

from common.mixins import JuridicoAdminPermissionMixin
from procesos.models import (
    AccionFutura,
    DetalleContrato,
    DocumentoProceso,
    Evento,
    HistorialEstado,
    Proceso,
    ProcesoParte,
)


class ProcesoParteInline(admin.TabularInline):
    model = ProcesoParte
    extra = 1
    autocomplete_fields = ["parte"]


class DetalleContratoInline(admin.StackedInline):
    model = DetalleContrato
    can_delete = False


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    fields = ("estado_anterior", "estado_nuevo", "fecha_modificacion", "observacion", "usuario")
    readonly_fields = ("usuario",)


class AccionFuturaInline(admin.TabularInline):
    model = AccionFutura
    extra = 0


@admin.register(Proceso)
class ProcesoAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = (
        "nro_correlativo",
        "categoria",
        "nurej",
        "juzgado",
        "estado_actual",
        "abogado_responsable",
        "activo",
    )
    list_filter = ("categoria", "estado_actual", "juzgado", "activo")
    search_fields = ("nro_correlativo", "nurej")
    autocomplete_fields = ["juzgado", "tipo_proceso"]
    inlines = [ProcesoParteInline, DetalleContratoInline, HistorialEstadoInline, AccionFuturaInline]


@admin.register(DocumentoProceso)
class DocumentoProcesoAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("proceso", "descripcion", "subido_por", "fecha_subida")

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "fecha", "hora", "proceso")
    list_filter = ("tipo",)