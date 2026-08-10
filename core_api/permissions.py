from rest_framework import permissions
from usuarios.models import es_admin_juridico, es_abogado

class EsAdminJuridicoOAdministrador(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return es_admin_juridico(request.user)


class PermisoProceso(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return es_admin_juridico(user) or es_abogado(user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        if es_admin_juridico(user):
            return True
        if es_abogado(user):
            return obj.abogado_responsable_id == user.id
        return False


class PermisoSubrecursoDeProceso(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        if es_admin_juridico(user):
            return True
        if es_abogado(user):
            return obj.proceso.abogado_responsable_id == user.id
        return False