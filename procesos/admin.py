from django.contrib import admin

from procesos.models import (
    AccionFutura,
    DetalleContrato,
    DocumentoProceso,
    HistorialEstado,
    Proceso,
    ProcesoParte,
)


class SoloAdminJuridicoMixin:
    """El módulo de procesos en el admin de Django es para el área
    jurídica (admin) y el superadmin. Los doctores usan las vistas propias."""

    def has_module_permission(self, request):
        return request.user.is_superuser or (
            hasattr(request.user, "perfil") and request.user.perfil.es_admin_juridico
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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
class ProcesoAdmin(SoloAdminJuridicoMixin, admin.ModelAdmin):
    list_display = (
        "nro_correlativo",
        "categoria",
        "nurej",
        "juzgado",
        "estado_actual",
        "doctor_responsable",
        "activo",
    )
    list_filter = ("categoria", "estado_actual", "juzgado", "activo")
    search_fields = ("nro_correlativo", "nurej")
    autocomplete_fields = ["juzgado", "tipo_proceso"]
    inlines = [ProcesoParteInline, DetalleContratoInline, HistorialEstadoInline, AccionFuturaInline]


@admin.register(DocumentoProceso)
class DocumentoProcesoAdmin(SoloAdminJuridicoMixin, admin.ModelAdmin):
    list_display = ("proceso", "descripcion", "subido_por", "fecha_subida")