from django.contrib import admin

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso


class CatalogoAdminMixin:

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


@admin.register(Categoria)
class CategoriaAdmin(CatalogoAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(TipoProceso)
class TipoProcesoAdmin(CatalogoAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "categoria")
    list_filter = ("categoria",)
    search_fields = ("nombre",)


@admin.register(Juzgado)
class JuzgadoAdmin(CatalogoAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo")
    list_filter = ("tipo",)
    search_fields = ("nombre",)


@admin.register(EstadoProceso)
class EstadoProcesoAdmin(CatalogoAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "orden", "es_final")


@admin.register(Parte)
class ParteAdmin(CatalogoAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo_persona", "nro_documento")
    search_fields = ("nombre", "nro_documento")