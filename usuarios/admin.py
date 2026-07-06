from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from usuarios.models import Perfil


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