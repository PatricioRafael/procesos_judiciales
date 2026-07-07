from rest_framework import permissions

from usuarios.models import es_admin_juridico, es_abogado, es_secretario


class EsAdminJuridicoOSuperadmin(permissions.BasePermission):
    """Solo admin jurídico o superadmin pueden gestionar catálogos.
    Cualquier usuario autenticado (incluido el secretario) puede leerlos."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return es_admin_juridico(request.user)


class PermisoProceso(permissions.BasePermission):
    """
    - Superadmin y admin jurídico: acceso total.
    - Abogado: puede ver (listar/detalle) todos los procesos, pero solo
      puede crear/editar/eliminar los que tiene asignados.
    - Secretario: solo lectura, nunca puede escribir.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if es_secretario(user):
            return False
        return es_admin_juridico(user) or es_abogado(user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        if es_secretario(user):
            return False
        if es_admin_juridico(user):
            return True
        if es_abogado(user):
            return obj.abogado_responsable_id == user.id
        return False


class PermisoSubrecursoDeProceso(permissions.BasePermission):
    """Para historial, acciones futuras y documentos: sigue la misma
    regla que el proceso padre."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        if es_secretario(user):
            return False
        if es_admin_juridico(user):
            return True
        if es_abogado(user):
            return obj.proceso.abogado_responsable_id == user.id
        return False