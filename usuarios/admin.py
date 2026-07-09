from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from usuarios.models import Perfil, RegistroAuditoria


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    fk_name = "usuario"


class UserAdmin(DjangoUserAdmin):
    inlines = (PerfilInline,)
    list_display = ("username", "get_full_name", "email", "get_rol", "is_active", "is_superuser")

    @admin.display(description="Rol")
    def get_rol(self, obj):
        if obj.is_superuser:
            return "Superadmin"
        return getattr(getattr(obj, "perfil", None), "get_rol_display", lambda: "-")()

    def get_inline_instances(self, request, obj=None):
        # Un usuario recién creado no tiene perfil hasta guardarse; evita error en /add
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def has_module_permission(self, request):
        # Solo el superadmin (área de sistemas) gestiona cuentas de usuario
        return request.user.is_superuser


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "usuario_texto", "accion", "modulo", "ip_address", "estado")
    list_filter = ("estado", "modulo")
    search_fields = ("usuario_texto", "accion", "ip_address")
    readonly_fields = [f.name for f in RegistroAuditoria._meta.fields]

    def has_add_permission(self, request):
        return False  # los registros solo se crean automáticamente, nunca a mano

    def has_change_permission(self, request, obj=None):
        return False  # de solo lectura, para no alterar el historial

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser