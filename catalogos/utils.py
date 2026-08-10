import re

# Palabras que indican que el nombre corresponde a una persona jurídica
# (empresa, institución u organización), no a una persona natural.
INDICADORES_JURIDICA = [
    "S.A.", "S.R.L.", "SRL", "S.A.C.", "LTDA", "LTDA.", "& CIA", "Y CIA",
    "EMPRESA", "CONSTRUCTORA", "SOCIEDAD", "CONSORCIO", "COMPAÑIA", "COMPAÑÍA",
    "GOBIERNO", "GOBERNACION", "GOBERNACIÓN", "MINISTERIO", "ALCALDIA", "ALCALDÍA",
    "MUNICIPIO", "MUNICIPAL", "DEPARTAMENTAL", "NACIONAL", "ESTATAL", "PUBLICA", "PÚBLICA",
    "COOPERATIVA", "ASOCIACION", "ASOCIACIÓN", "FUNDACION", "FUNDACIÓN", "SINDICATO",
    "FEDERACION", "FEDERACIÓN", "COMITE", "COMITÉ", "COLEGIO",
    "UNIVERSIDAD", "INSTITUTO", "BANCO", "CAJA", "GESTORA", "SEGURO", "SEGUROS",
    "SERVICIO", "SERVICIOS", "ADMINISTRADORA", "AGENCIA", "CORPORACION", "CORPORACIÓN",
    "GADP", "G.A.D.P", "MINISTERIO PUBLICO", "MINISTERIO PÚBLICO",
]


def detectar_tipo_persona(nombre):
    from catalogos.models import Parte

    texto = (nombre or "").upper()
    for indicador in INDICADORES_JURIDICA:
        if indicador in texto:
            return Parte.TipoPersona.JURIDICA
    return Parte.TipoPersona.NATURAL


def normalizar(texto):
    return re.sub(r"\s+", " ", (texto or "")).strip()


def normalizar_mayusculas(texto):
    return normalizar(texto).upper()


def obtener_o_crear_parte(nombre):
    from catalogos.models import Parte

    nombre = normalizar_mayusculas(nombre)
    if not nombre:
        return None
    existente = Parte.objects.filter(nombre__iexact=nombre).first()
    if existente:
        return existente
    return Parte.objects.create(nombre=nombre, tipo_persona=detectar_tipo_persona(nombre))


def obtener_o_crear_juzgado(nombre):
    from catalogos.models import Juzgado

    nombre = normalizar_mayusculas(nombre) or "SIN ESPECIFICAR"
    existente = Juzgado.objects.filter(nombre__iexact=nombre).first()
    if existente:
        return existente
    return Juzgado.objects.create(nombre=nombre)


def obtener_o_crear_tipo_proceso(categoria, nombre):
    from catalogos.models import TipoProceso

    nombre = normalizar_mayusculas(nombre)
    if not nombre:
        return None
    existente = TipoProceso.objects.filter(categoria=categoria, nombre__iexact=nombre).first()
    if existente:
        return existente
    return TipoProceso.objects.create(categoria=categoria, nombre=nombre)