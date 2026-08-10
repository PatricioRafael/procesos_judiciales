from datetime import date, timedelta

DIAS_AVISO = 7


def _clasificar(fecha_limite, hoy):
    dias = (fecha_limite - hoy).days
    if dias < 0:
        return "vencido", f"Venció hace {abs(dias)} día{'s' if abs(dias) != 1 else ''}"
    if dias == 0:
        return "hoy", "Vence hoy"
    if dias == 1:
        return "urgente", "Vence mañana"
    if dias <= 3:
        return "urgente", f"Vence en {dias} días"
    return "proximo", f"Vence en {dias} días"


def notificaciones(request):
    if not request.user.is_authenticated:
        return {}

    from procesos.models import AccionFutura, Evento

    hoy = date.today()
    limite = hoy + timedelta(days=DIAS_AVISO)
    items = []

    acciones = AccionFutura.objects.filter(
        completada=False, fecha_limite__isnull=False, fecha_limite__lte=limite
    ).select_related("proceso")
    for a in acciones:
        tipo, texto_urgencia = _clasificar(a.fecha_limite, hoy)
        items.append({
            "texto": a.descripcion,
            "categoria": "Tarea",
            "tipo": tipo,
            "urgencia_texto": texto_urgencia,
            "fecha": a.fecha_limite,
            "proceso": a.proceso,
        })

    eventos = Evento.objects.filter(fecha__lte=limite, fecha__gte=hoy - timedelta(days=1)).select_related("proceso")
    for e in eventos:
        tipo, texto_urgencia = _clasificar(e.fecha, hoy)
        items.append({
            "texto": e.titulo,
            "categoria": e.get_tipo_display(),
            "tipo": tipo,
            "urgencia_texto": texto_urgencia,
            "fecha": e.fecha,
            "proceso": e.proceso,
        })

    orden_urgencia = {"vencido": 0, "hoy": 1, "urgente": 2, "proximo": 3}
    items.sort(key=lambda x: (orden_urgencia[x["tipo"]], x["fecha"]))

    urgentes = [i for i in items if i["tipo"] in ("vencido", "hoy", "urgente")]

    return {
        "notificaciones_lista": items[:10],
        "notificaciones_total": len(items),
        "notificaciones_urgentes": len(urgentes),
    }