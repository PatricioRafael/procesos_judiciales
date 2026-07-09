from usuarios.middleware import get_client_ip, get_current_request


def registrar(accion, modulo, detalle=None, estado="EXITO"):
    from usuarios.models import RegistroAuditoria

    request = get_current_request()
    usuario = getattr(request, "user", None) if request else None
    if usuario is not None and not usuario.is_authenticated:
        usuario = None

    RegistroAuditoria.objects.create(
        usuario=usuario,
        usuario_texto=usuario.username if usuario else "Sistema",
        accion=accion,
        modulo=modulo,
        ip_address=get_client_ip(request),
        estado=estado,
        detalle=detalle or {},
    )