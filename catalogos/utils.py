import re


def normalizar(texto):
    """Quita espacios sobrantes y al inicio/final."""
    return re.sub(r"\s+", " ", (texto or "")).strip()


def obtener_o_crear_parte(nombre):
    """Busca una Parte ignorando mayúsculas/minúsculas antes de crear una nueva,
    para no duplicar 'GADP', 'Gadp' y 'gadp' como tres registros distintos."""
    from catalogos.models import Parte

    nombre = normalizar(nombre)
    if not nombre:
        return None
    existente = Parte.objects.filter(nombre__iexact=nombre).first()
    if existente:
        return existente
    return Parte.objects.create(nombre=nombre)


def obtener_o_crear_juzgado(nombre):
    from catalogos.models import Juzgado

    nombre = normalizar(nombre) or "Sin especificar"
    existente = Juzgado.objects.filter(nombre__iexact=nombre).first()
    if existente:
        return existente
    return Juzgado.objects.create(nombre=nombre)


def obtener_o_crear_tipo_proceso(categoria, nombre):
    from catalogos.models import TipoProceso

    nombre = normalizar(nombre)
    if not nombre:
        return None
    existente = TipoProceso.objects.filter(categoria=categoria, nombre__iexact=nombre).first()
    if existente:
        return existente
    return TipoProceso.objects.create(categoria=categoria, nombre=nombre)