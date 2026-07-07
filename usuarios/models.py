from django.conf import settings
from django.db import models


class Perfil(models.Model):

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador jurídico"
        ABOGADO = "ABOGADO", "Abogado"
        SECRETARIO = "SECRETARIO", "Secretario"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.ABOGADO)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.get_rol_display()})"

    @property
    def es_admin_juridico(self):
        return self.rol == self.Rol.ADMIN

    @property
    def es_abogado(self):
        return self.rol == self.Rol.ABOGADO
    
    @property
    def es_secretario(self):
        return self.rol == self.Rol.SECRETARIO


def es_superadmin(user):
    return user.is_authenticated and user.is_superuser


def es_admin_juridico(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, "perfil") and user.perfil.rol == Perfil.Rol.ADMIN and user.perfil.activo


def es_abogado(user):
    if not user.is_authenticated:
        return False
    return hasattr(user, "perfil") and user.perfil.rol == Perfil.Rol.ABOGADO and user.perfil.activo

def es_secretario(user):
    if not user.is_authenticated:
        return False
    return hasattr(user, "perfil") and user.perfil.rol == Perfil.Rol.SECRETARIO and user.perfil.activo