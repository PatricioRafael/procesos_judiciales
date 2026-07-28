from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView, View
from django.db.models import Count

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from catalogos.utils import obtener_o_crear_juzgado, obtener_o_crear_parte, obtener_o_crear_tipo_proceso
from common.mixins import aplicar_clases_bootstrap
from procesos.forms import AccionFuturaForm, EventoForm, HistorialEstadoForm, ProcesoForm
from procesos.models import DetalleContrato, DocumentoProceso, Evento, HistorialEstado, Proceso, ProcesoParte
from usuarios.models import es_admin_juridico, es_abogado


class ProcesoCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProcesoForm
    template_name = "procesos/formulario.html"

    def test_func(self):
        return es_admin_juridico(self.request.user) or es_abogado(self.request.user)

    def handle_no_permission(self):
        raise PermissionDenied("Tu rol no tiene permiso para registrar procesos nuevos.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_actual"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["partes_existentes"] = Parte.objects.order_by("nombre").values_list("nombre", flat=True).distinct()
        ctx["juzgados_existentes"] = Juzgado.objects.order_by("nombre").values_list("nombre", flat=True)
        ctx["tipos_existentes"] = TipoProceso.objects.order_by("nombre").values_list("nombre", flat=True).distinct()
        return ctx

    MAX_ARCHIVOS = 3
    MAX_TAMANO_MB = 5

    def post(self, request, *args, **kwargs):
        archivos = request.FILES.getlist("documentos")
        error = self._validar_documentos(archivos)
        if error:
            form = self.get_form()
            form.full_clean()
            messages.error(request, error)
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def _validar_documentos(self, archivos):
        if len(archivos) > self.MAX_ARCHIVOS:
            return f"Puedes adjuntar como máximo {self.MAX_ARCHIVOS} documentos por proceso."
        for archivo in archivos:
            if not archivo.name.lower().endswith(".pdf"):
                return f"'{archivo.name}' no es un PDF. Solo se aceptan archivos .pdf."
            if archivo.size > self.MAX_TAMANO_MB * 1024 * 1024:
                return f"'{archivo.name}' pesa demasiado ({archivo.size / 1024 / 1024:.1f} MB). El máximo permitido es {self.MAX_TAMANO_MB} MB."
        return None

    def form_valid(self, form):
        datos = form.cleaned_data
        user = self.request.user

        juzgado = obtener_o_crear_juzgado(datos["juzgado"])

        ultimo = Proceso.objects.filter(categoria=datos["categoria"]).count()
        siguiente_nro = str(ultimo + 1)

        profesional_elegido = datos.get("profesional_a_cargo")
        abogado_final = profesional_elegido if profesional_elegido else (user if es_abogado(user) else None)

        from datetime import date

        proceso = Proceso.objects.create(
            nro_correlativo=siguiente_nro,
            nurej=datos.get("nurej") or None,
            categoria=datos["categoria"],
            juzgado=juzgado,
            estado_actual=datos["estado_actual"],
            abogado_responsable=abogado_final,
            fecha_registro=datos.get("fecha_registro") or date.today(),
        )

        # Demandantes (uno o varios)
        for nombre_activa in getattr(form, "partes_activas_lista", []):
            parte = obtener_o_crear_parte(nombre_activa)
            if parte:
                ProcesoParte.objects.get_or_create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.ACTIVA)

        # Demandado: en Contencioso siempre es el GADP; en las demás, lo que escribió el usuario
        if datos["categoria"].nombre == "Contencioso":
            parte = obtener_o_crear_parte("Gobierno Autónomo Departamental de Potosí")
            ProcesoParte.objects.get_or_create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.PASIVA)
            if datos.get("proyecto_motivo"):
                DetalleContrato.objects.create(proceso=proceso, proyecto=datos["proyecto_motivo"])
        else:
            for nombre_pasiva in getattr(form, "partes_pasivas_lista", []):
                parte = obtener_o_crear_parte(nombre_pasiva)
                if parte:
                    ProcesoParte.objects.get_or_create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.PASIVA)
            tipo_proceso = obtener_o_crear_tipo_proceso(datos["categoria"], datos.get("proyecto_motivo"))
            if tipo_proceso:
                proceso.tipo_proceso = tipo_proceso
                proceso.save(update_fields=["tipo_proceso"])

        # Estado actual del proceso, tal como en el documento oficial: se guarda como
        # la primera entrada del historial.
        if datos.get("estado_actual_texto"):
            HistorialEstado.objects.create(
                proceso=proceso, estado_nuevo=datos["estado_actual"],
                usuario=user, observacion=datos["estado_actual_texto"],
            )

        # Documentos adjuntos (máximo 3, ya validado en post())
        for archivo in self.request.FILES.getlist("documentos"):
            DocumentoProceso.objects.create(
                proceso=proceso, archivo=archivo, subido_por=user, descripcion=archivo.name
            )

        messages.success(self.request, f"Proceso Nº {proceso.nro_correlativo} registrado correctamente.")
        return redirect(proceso.get_absolute_url())


def _filtrar_procesos(request):
    qs = Proceso.objects.select_related(
        "categoria", "juzgado", "estado_actual", "abogado_responsable"
    ).order_by("-actualizado_en")

    categoria = request.GET.get("categoria")
    estado = request.GET.get("estado")
    q = request.GET.get("q")
    mios = request.GET.get("mios")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if categoria:
        qs = qs.filter(categoria_id=categoria)
    if estado:
        qs = qs.filter(estado_actual_id=estado)
    if q:
        qs = qs.filter(nro_correlativo__icontains=q) | qs.filter(nurej__icontains=q)
    if fecha_desde:
        qs = qs.filter(fecha_registro__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_registro__lte=fecha_hasta)
    if mios and es_abogado(request.user):
        qs = qs.filter(abogado_responsable=request.user)
    return qs


class ProcesoListView(LoginRequiredMixin, ListView):
    model = Proceso
    template_name = "procesos/listado.html"
    context_object_name = "procesos"
    paginate_by = 25

    def get_queryset(self):
        return _filtrar_procesos(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorias"] = Categoria.objects.all()
        ctx["estados"] = EstadoProceso.objects.all()
        return ctx


class ProcesoDetailView(LoginRequiredMixin, DetailView):
    model = Proceso
    template_name = "procesos/detalle.html"
    context_object_name = "proceso"

    def get_queryset(self):
        return Proceso.objects.select_related(
            "categoria", "tipo_proceso", "juzgado", "estado_actual", "abogado_responsable"
        ).prefetch_related("partes__parte", "historial__estado_nuevo", "acciones_futuras", "documentos")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        proceso = self.object
        user = self.request.user
        ctx["puede_editar"] = es_admin_juridico(user) or (
            es_abogado(user) and proceso.abogado_responsable_id == user.id
        )
        ctx["linea_tiempo"] = self._construir_linea_tiempo(proceso)
        return ctx

    def _construir_linea_tiempo(self, proceso):
        """Junta en una sola lista cronológica: actuaciones, eventos,
        acciones futuras, documentos y las ediciones registradas en auditoría."""
        from usuarios.models import RegistroAuditoria

        items = []

        for h in proceso.historial.all():
            items.append({
                "fecha": h.creado_en,
                "fecha_visible": h.fecha_modificacion or h.creado_en.date(),
                "tipo": "actuacion",
                "icono": "bi-clock-history",
                "color": "var(--color-red)",
                "titulo": f"Actuación: {h.estado_nuevo.nombre}",
                "detalle": h.observacion,
                "usuario": h.usuario,
            })

        for e in proceso.eventos.all():
            items.append({
                "fecha": e.creado_en,
                "fecha_visible": e.fecha,
                "tipo": "evento",
                "icono": "bi-calendar-event",
                "color": "var(--color-gold)",
                "titulo": f"{e.get_tipo_display()}: {e.titulo}",
                "detalle": e.descripcion,
                "usuario": e.creado_por,
            })

        for a in proceso.acciones_futuras.all():
            items.append({
                "fecha": a.creado_en,
                "fecha_visible": a.fecha_limite or a.creado_en.date(),
                "tipo": "accion",
                "icono": "bi-clipboard-check",
                "color": "#1f9d55" if a.completada else "var(--color-gray)",
                "titulo": "Acción futura" + (" (completada)" if a.completada else ""),
                "detalle": a.descripcion,
                "usuario": a.responsable,
            })

        for d in proceso.documentos.all():
            items.append({
                "fecha": d.fecha_subida,
                "fecha_visible": d.fecha_subida.date(),
                "tipo": "documento",
                "icono": "bi-file-earmark-arrow-up",
                "color": "var(--color-ink)",
                "titulo": "Documento adjuntado",
                "detalle": d.descripcion or d.archivo.name,
                "usuario": d.subido_por,
            })

        for r in RegistroAuditoria.objects.filter(detalle__proceso_id=proceso.id, accion__in=["Creado Proceso", "Editado Proceso"]):
            cambios = (r.detalle or {}).get("cambios", {})
            detalle_texto = "; ".join(
                f"{etiqueta}: «{c['antes']}» → «{c['ahora']}»" for etiqueta, c in cambios.items()
            )
            items.append({
                "fecha": r.creado_en,
                "fecha_visible": r.creado_en.date(),
                "tipo": "auditoria",
                "icono": "bi-pencil-square" if r.accion == "Editado Proceso" else "bi-plus-circle",
                "color": "var(--color-gray)",
                "titulo": r.accion,
                "detalle": detalle_texto,
                "usuario": r.usuario,
            })

        items.sort(key=lambda x: x["fecha"], reverse=True)
        return items


class PuedeEditarProcesoMixin(UserPassesTestMixin):
    def test_func(self):
        proceso = self.get_object()
        user = self.request.user
        if es_admin_juridico(user):
            return True
        if es_abogado(user):
            return proceso.abogado_responsable_id == user.id
        return False

    def handle_no_permission(self):
        raise PermissionDenied("Solo el abogado responsable o el área jurídica pueden editar este proceso.")


class ProcesoUpdateView(LoginRequiredMixin, PuedeEditarProcesoMixin, UpdateView):
    model = Proceso
    fields = ["nurej", "juzgado", "estado_actual", "activo"]
    template_name = "procesos/editar.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        aplicar_clases_bootstrap(form)
        return form

    def form_valid(self, form):
        messages.success(self.request, "Proceso actualizado correctamente.")
        return super().form_valid(form)


class AgregarHistorialView(LoginRequiredMixin, PuedeEditarProcesoMixin, CreateView):
    model = Proceso  # se usa solo para que el mixin de permisos reutilice get_object()
    form_class = HistorialEstadoForm
    template_name = "procesos/agregar_historial.html"

    def get_object(self):
        return get_object_or_404(Proceso, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proceso"] = self.get_object()
        return ctx

    def form_valid(self, form):
        proceso = self.get_object()
        historial = form.save(commit=False)
        historial.proceso = proceso
        historial.usuario = self.request.user
        historial.estado_anterior = proceso.estado_actual
        historial.save()
        proceso.estado_actual = historial.estado_nuevo
        proceso.save(update_fields=["estado_actual", "actualizado_en"])
        messages.success(self.request, "Se registró la actuación en el historial.")
        return redirect(proceso.get_absolute_url())


class AgregarAccionFuturaView(LoginRequiredMixin, PuedeEditarProcesoMixin, CreateView):
    model = Proceso
    form_class = AccionFuturaForm
    template_name = "procesos/agregar_accion.html"

    def get_object(self):
        return get_object_or_404(Proceso, pk=self.kwargs["pk"])

    def get_initial(self):
        initial = super().get_initial()
        proceso = self.get_object()
        if proceso.abogado_responsable_id:
            initial["responsable"] = proceso.abogado_responsable_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proceso"] = self.get_object()
        return ctx

    def form_valid(self, form):
        proceso = self.get_object()
        accion = form.save(commit=False)
        accion.proceso = proceso
        accion.save()
        messages.success(self.request, "Acción futura registrada.")
        return redirect(proceso.get_absolute_url())


class ProcesoDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "procesos/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        todos = Proceso.objects.all()
        total = todos.count() or 1

        ctx["total_procesos"] = todos.count()
        ctx["total_activos"] = todos.filter(activo=True).count()
        ctx["casos_apelacion"] = todos.filter(estado_actual__nombre__icontains="apelación").count()
        ctx["procesos_concluidos"] = todos.filter(estado_actual__es_final=True).count()

        from procesos.models import AccionFutura
        ctx["tareas_pendientes"] = AccionFutura.objects.filter(completada=False).count()

        # Donut: distribución por cada estado con procesos
        PALETA = [
            "#8b0000", "#c5a059", "#1c1917", "#a8a29e", "#1f9d55",
            "#b45309", "#6b21a8", "#0e7490", "#be123c", "#4d7c0f",
        ]
        estados_con_total = (
            EstadoProceso.objects.annotate(total_procesos=Count("procesos"))
            .filter(total_procesos__gt=0)
            .order_by("-total_procesos")
        )

        segmentos = []
        acumulado = 0
        for i, estado in enumerate(estados_con_total):
            porcentaje = estado.total_procesos / total * 100
            color = PALETA[i % len(PALETA)]
            segmentos.append({
                "nombre": estado.nombre,
                "cantidad": estado.total_procesos,
                "porcentaje": round(porcentaje, 1),
                "color": color,
                "desde": round(acumulado, 2),
                "hasta": round(acumulado + porcentaje, 2),
            })
            acumulado += porcentaje

        ctx["segmentos_estado"] = segmentos
        ctx["gradiente_estados"] = ", ".join(
            f"{s['color']} {s['desde']}% {s['hasta']}%" for s in segmentos
        ) or "var(--color-border) 0% 100%"

        # Barras: procesos por categoría
        categorias_con_total = (
            Categoria.objects.annotate(total_procesos=Count("procesos")).order_by("-total_procesos")
        )
        maximo = max((c.total_procesos for c in categorias_con_total), default=1) or 1
        for c in categorias_con_total:
            c.porcentaje_barra = round(c.total_procesos / maximo * 100)
        ctx["categorias_con_total"] = categorias_con_total

        return ctx


class CalendarioView(LoginRequiredMixin, TemplateView):
    template_name = "procesos/calendario.html"

    def get_context_data(self, **kwargs):
        import calendar as cal_module
        from datetime import date

        ctx = super().get_context_data(**kwargs)
        hoy = date.today()
        anio = int(self.request.GET.get("anio", hoy.year))
        mes = int(self.request.GET.get("mes", hoy.month))

        eventos_mes = Evento.objects.filter(fecha__year=anio, fecha__month=mes).select_related("proceso")
        eventos_por_dia = {}
        for ev in eventos_mes:
            eventos_por_dia.setdefault(ev.fecha.day, []).append(ev)

        cal = cal_module.Calendar(firstweekday=0)  # lunes
        semanas = cal.monthdayscalendar(anio, mes)

        mes_anterior = mes - 1 if mes > 1 else 12
        anio_mes_anterior = anio if mes > 1 else anio - 1
        mes_siguiente = mes + 1 if mes < 12 else 1
        anio_mes_siguiente = anio if mes < 12 else anio + 1

        MESES_ES = [
            "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        ]

        ctx.update({
            "semanas": semanas,
            "eventos_por_dia": eventos_por_dia,
            "nombre_mes": MESES_ES[mes],
            "anio": anio, "mes": mes, "hoy": hoy,
            "mes_anterior": mes_anterior, "anio_mes_anterior": anio_mes_anterior,
            "mes_siguiente": mes_siguiente, "anio_mes_siguiente": anio_mes_siguiente,
            "proximos_eventos": Evento.objects.filter(fecha__gte=hoy).select_related("proceso")[:5],
        })
        return ctx


class AgregarEventoView(LoginRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "procesos/agregar_evento.html"

    def form_valid(self, form):
        evento = form.save(commit=False)
        evento.creado_por = self.request.user
        evento.save()
        messages.success(self.request, "Evento agregado al calendario.")
        return redirect("procesos:calendario")


class DocumentosGlobalView(LoginRequiredMixin, TemplateView):
    template_name = "procesos/documentos.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["documentos"] = DocumentoProceso.objects.select_related("proceso", "subido_por").order_by("-fecha_subida")[:50]
        return ctx


def exportar_excel(request):
    import openpyxl
    from django.http import HttpResponse

    procesos = _filtrar_procesos(request)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Procesos"
    ws.append(["Nº", "NUREJ", "Categoría", "Demandante", "Demandado", "Juzgado", "Estado", "Responsable"])

    for p in procesos:
        activa = p.partes_activas.first()
        pasiva = p.partes_pasivas.first()
        ws.append([
            p.nro_correlativo,
            p.nurej or "",
            p.categoria.nombre,
            activa.parte.nombre if activa else "",
            pasiva.parte.nombre if pasiva else "",
            p.juzgado.nombre,
            p.estado_actual.nombre,
            p.abogado_responsable.get_full_name() if p.abogado_responsable else "",
        ])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="procesos.xlsx"'
    wb.save(response)
    return response


def exportar_pdf(request):
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

    procesos = _filtrar_procesos(request)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="procesos.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    estilos = getSampleStyleSheet()
    estilo_celda = ParagraphStyle("celda", parent=estilos["Normal"], fontSize=8, leading=10)
    estilo_encabezado = ParagraphStyle("encabezado", parent=estilos["Normal"], fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold")

    elementos = [Paragraph("Listado de Procesos Judiciales - GADP", estilos["Title"])]

    encabezados = ["Nº", "NUREJ", "Categoría", "Demandante", "Demandado", "Juzgado", "Estado"]
    datos = [[Paragraph(h, estilo_encabezado) for h in encabezados]]

    for p in procesos:
        activa = p.partes_activas.first()
        pasiva = p.partes_pasivas.first()
        datos.append([
            Paragraph(p.nro_correlativo, estilo_celda),
            Paragraph(p.nurej or "-", estilo_celda),
            Paragraph(p.categoria.nombre, estilo_celda),
            Paragraph(activa.parte.nombre if activa else "-", estilo_celda),
            Paragraph(pasiva.parte.nombre if pasiva else "-", estilo_celda),
            Paragraph(p.juzgado.nombre, estilo_celda),
            Paragraph(p.estado_actual.nombre, estilo_celda),
        ])

    # Anchos de columna ajustados para hoja horizontal (carta apaisada = ~10 pulgadas útiles)
    anchos = [0.4 * 72, 0.9 * 72, 1.1 * 72, 2.3 * 72, 2.3 * 72, 1.7 * 72, 1.3 * 72]

    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c1917")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f8f6")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    return response


def exportar_proceso_pdf(request, pk):
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    proceso = get_object_or_404(
        Proceso.objects.select_related("categoria", "juzgado", "estado_actual", "abogado_responsable")
        .prefetch_related("partes__parte", "historial__estado_nuevo", "acciones_futuras"),
        pk=pk,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="proceso_{proceso.nro_correlativo}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm)
    estilos = getSampleStyleSheet()
    estilo_celda = ParagraphStyle("celda", parent=estilos["Normal"], fontSize=9, leading=12)
    estilo_etiqueta = ParagraphStyle("etiqueta", parent=estilos["Normal"], fontSize=9, leading=12, textColor=colors.white, fontName="Helvetica-Bold")
    elementos = []

    elementos.append(Paragraph("Gobernación Autónoma Departamental de Potosí", estilos["Heading2"]))
    elementos.append(Paragraph(f"Expediente Nº {proceso.nro_correlativo} — {proceso.categoria.nombre}", estilos["Title"]))
    elementos.append(Spacer(1, 12))

    partes_activas = ", ".join(pp.parte.nombre for pp in proceso.partes_activas) or "-"
    partes_pasivas = ", ".join(pp.parte.nombre for pp in proceso.partes_pasivas) or "-"

    datos_generales = [
        [Paragraph("NUREJ", estilo_etiqueta), Paragraph(proceso.nurej or "Sin asignar", estilo_celda)],
        [Paragraph("Juzgado", estilo_etiqueta), Paragraph(proceso.juzgado.nombre, estilo_celda)],
        [Paragraph("Estado actual", estilo_etiqueta), Paragraph(proceso.estado_actual.nombre, estilo_celda)],
        [Paragraph("Demandante", estilo_etiqueta), Paragraph(partes_activas, estilo_celda)],
        [Paragraph("Demandado", estilo_etiqueta), Paragraph(partes_pasivas, estilo_celda)],
        [Paragraph("Abogado a cargo", estilo_etiqueta), Paragraph(proceso.abogado_a_cargo or "Sin asignar", estilo_celda)],
    ]
    tabla_general = Table(datos_generales, colWidths=[4 * cm, 12 * cm])
    tabla_general.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1c1917")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_general)
    elementos.append(Spacer(1, 18))

    elementos.append(Paragraph("Historial de actuaciones", estilos["Heading3"]))
    if proceso.historial.exists():
        datos_historial = [[
            Paragraph("Fecha", estilo_etiqueta), Paragraph("Estado", estilo_etiqueta), Paragraph("Observación", estilo_etiqueta),
        ]]
        for h in proceso.historial.all():
            fecha = h.fecha_modificacion or h.creado_en.date()
            datos_historial.append([
                Paragraph(fecha.strftime("%d/%m/%Y"), estilo_celda),
                Paragraph(h.estado_nuevo.nombre, estilo_celda),
                Paragraph(h.observacion or "", estilo_celda),
            ])
        tabla_historial = Table(datos_historial, colWidths=[2.5 * cm, 3.5 * cm, 10 * cm], repeatRows=1)
        tabla_historial.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c1917")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla_historial)
    else:
        elementos.append(Paragraph("Sin actuaciones registradas.", estilos["Normal"]))

    doc.build(elementos)
    return response


class ToggleAccionFuturaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        from procesos.models import AccionFutura

        accion = get_object_or_404(AccionFutura, pk=pk)
        proceso = accion.proceso
        user = request.user

        puede = es_admin_juridico(user) or (es_abogado(user) and proceso.abogado_responsable_id == user.id)
        if not puede:
            messages.error(request, "Solo el abogado responsable de este proceso o el área jurídica pueden marcar sus tareas.")
            return redirect("procesos:detalle", pk=proceso.pk)

        accion.completada = not accion.completada
        accion.save(update_fields=["completada"])
        return redirect("procesos:detalle", pk=proceso.pk)
