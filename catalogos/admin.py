from django.contrib import admin

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from common.mixins import JuridicoAdminPermissionMixin


@admin.register(Categoria)
class CategoriaAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("nombre", "orden")


@admin.register(TipoProceso)
class TipoProcesoAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("nombre", "categoria")
    list_filter = ("categoria",)
    search_fields = ("nombre",)


@admin.register(Juzgado)
class JuzgadoAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo")
    list_filter = ("tipo",)
    search_fields = ("nombre",)


@admin.register(EstadoProceso)
class EstadoProcesoAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("nombre", "orden", "es_final")


@admin.register(Parte)
class ParteAdmin(JuridicoAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("nombre", "tipo_persona")
    search_fields = ("nombre",)