from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from usuarios.auditoria import registrar
from usuarios.middleware import get_client_ip, get_current_request
from usuarios.models import Perfil, RegistroAuditoria


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        Perfil.objects.get_or_create(usuario=instance)


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    RegistroAuditoria.objects.create(
        usuario=user, usuario_texto=user.username, accion="Inicio de sesión",
        modulo="Login Global", ip_address=get_client_ip(request), estado=RegistroAuditoria.Estado.EXITO,
    )


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    if user:
        RegistroAuditoria.objects.create(
            usuario=user, usuario_texto=user.username, accion="Cierre de sesión",
            modulo="Login Global", ip_address=get_client_ip(request), estado=RegistroAuditoria.Estado.EXITO,
        )


@receiver(user_login_failed)
def registrar_login_fallido(sender, credentials, request=None, **kwargs):
    request = request or get_current_request()
    RegistroAuditoria.objects.create(
        usuario=None, usuario_texto=credentials.get("username", "desconocido"),
        accion="Acceso fallido", modulo="Login Global",
        ip_address=get_client_ip(request), estado=RegistroAuditoria.Estado.FALLO,
    )


@receiver(post_save, sender=Perfil)
def auditar_cambio_rol(sender, instance, created, **kwargs):
    accion = "Usuario creado" if created else "Cambio Privilegios"
    registrar(accion, modulo="User Management", detalle={
        "usuario": instance.usuario.username, "rol": instance.get_rol_display(),
    })