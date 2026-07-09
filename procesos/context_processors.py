from datetime import date, timedelta


def notificaciones(request):
    if not request.user.is_authenticated:
        return {}

    from procesos.models import AccionFutura, Evento

    hoy = date.today()
    en_7_dias = hoy + timedelta(days=7)

    acciones_vencidas = AccionFutura.objects.filter(
        completada=False, fecha_limite__lt=hoy
    ).select_related("proceso")
    acciones_proximas = AccionFutura.objects.filter(
        completada=False, fecha_limite__gte=hoy, fecha_limite__lte=en_7_dias
    ).select_related("proceso")
    eventos_proximos = Evento.objects.filter(
        fecha__gte=hoy, fecha__lte=en_7_dias
    ).select_related("proceso")

    items = []
    for a in acciones_vencidas:
        items.append({"texto": a.descripcion, "tipo": "vencido", "fecha": a.fecha_limite, "proceso": a.proceso})
    for a in acciones_proximas:
        items.append({"texto": a.descripcion, "tipo": "proximo", "fecha": a.fecha_limite, "proceso": a.proceso})
    for e in eventos_proximos:
        items.append({"texto": e.titulo, "tipo": "evento", "fecha": e.fecha, "proceso": e.proceso})

    items.sort(key=lambda x: x["fecha"])

    return {
        "notificaciones_lista": items[:8],
        "notificaciones_total": len(items),
    }