from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView
from django.db.models import Count
from django.views.generic import TemplateView

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from procesos.forms import AccionFuturaForm, EventoForm, HistorialEstadoForm, ProcesoForm
from procesos.models import DetalleContrato, DocumentoProceso, Evento, HistorialEstado, Proceso, ProcesoParte
from usuarios.models import es_admin_juridico, es_abogado, es_secretario

def _dividir_nombres(texto):
    """'Juan Pérez, María Gómez' -> ['Juan Pérez', 'María Gómez']"""
    return [n.strip() for n in texto.split(",") if n.strip()]


class ProcesoCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProcesoForm
    template_name = "procesos/formulario.html"

    def test_func(self):
        return es_admin_juridico(self.request.user) or es_abogado(self.request.user)

    def handle_no_permission(self):
        raise PermissionDenied("Tu rol no tiene permiso para registrar procesos nuevos.")

    def post(self, request, *args, **kwargs):
        # Límite de documentos adjuntos: máximo 3 por proceso
        archivos = request.FILES.getlist("documentos")
        if len(archivos) > 3:
            form = self.get_form()
            form.full_clean()
            messages.error(request, "Puedes adjuntar como máximo 3 documentos por proceso.")
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        datos = form.cleaned_data
        user = self.request.user

        juzgado, _ = Juzgado.objects.get_or_create(nombre=datos["juzgado"].strip())

        ultimo = Proceso.objects.filter(categoria=datos["categoria"]).count()
        siguiente_nro = str(ultimo + 1)

        proceso = Proceso.objects.create(
            nro_correlativo=siguiente_nro,
            nurej=datos.get("nurej") or None,
            categoria=datos["categoria"],
            juzgado=juzgado,
            estado_actual=datos["estado_actual"],
            abogado_referencia=datos.get("abogado_referencia", ""),
            abogado_responsable=user if es_abogado(user) else None,
        )

        # Demandante
        nombre_activa = datos["parte_activa"].strip()
        if nombre_activa:
            parte, _ = Parte.objects.get_or_create(nombre=nombre_activa)
            ProcesoParte.objects.create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.ACTIVA)

        # Demandado: en Contencioso siempre es el GADP; en las demás, lo que escribió el usuario
        if datos["categoria"].nombre == "Contencioso":
            parte, _ = Parte.objects.get_or_create(nombre="Gobierno Autónomo Departamental de Potosí")
            ProcesoParte.objects.create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.PASIVA)
            if datos.get("proyecto_motivo"):
                DetalleContrato.objects.create(proceso=proceso, proyecto=datos["proyecto_motivo"])
        else:
            nombre_pasiva = datos.get("parte_pasiva", "").strip()
            if nombre_pasiva:
                parte, _ = Parte.objects.get_or_create(nombre=nombre_pasiva)
                ProcesoParte.objects.create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.PASIVA)
            if datos.get("proyecto_motivo"):
                tipo_proceso, _ = TipoProceso.objects.get_or_create(
                    categoria=datos["categoria"], nombre=datos["proyecto_motivo"].strip()
                )
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
    
from django.views.generic import DetailView, ListView

from catalogos.models import Categoria, EstadoProceso

def _filtrar_procesos(request):
    qs = Proceso.objects.select_related(
        "categoria", "juzgado", "estado_actual", "abogado_responsable"
    ).order_by("-actualizado_en")

    categoria = request.GET.get("categoria")
    estado = request.GET.get("estado")
    q = request.GET.get("q")
    mios = request.GET.get("mios")
    fecha = request.GET.get("fecha")

    if categoria:
        qs = qs.filter(categoria_id=categoria)
    if estado:
        qs = qs.filter(estado_actual_id=estado)
    if q:
        qs = qs.filter(nro_correlativo__icontains=q) | qs.filter(nurej__icontains=q)
    if fecha:
        qs = qs.filter(fecha_registro=fecha)
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

        todos = Proceso.objects.all()

        from procesos.models import AccionFutura

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
        return ctx
    
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, UpdateView

from procesos.forms import AccionFuturaForm, HistorialEstadoForm


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
    fields = ["nurej", "juzgado", "estado_actual", "fecha_registro", "activo"]
    template_name = "procesos/editar.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            css = "form-select" if hasattr(field.widget, "choices") else "form-control"
            if field.widget.input_type == "checkbox":
                css = "form-check-input"
            field.widget.attrs["class"] = css
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

        # Donut: activos vs concluidos
        activos_count = todos.filter(estado_actual__es_final=False).count()
        concluidos_count = todos.filter(estado_actual__es_final=True).count()
        ctx["pct_activos"] = round(activos_count / total * 100)
        ctx["pct_concluidos"] = round(concluidos_count / total * 100)

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
        from procesos.models import Evento

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

        ctx.update({
            "semanas": semanas,
            "eventos_por_dia": eventos_por_dia,
            "nombre_mes": cal_module.month_name[mes].capitalize(),
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
        from procesos.models import DocumentoProceso
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
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    procesos = _filtrar_procesos(request)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="procesos.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    estilos = getSampleStyleSheet()
    elementos = [Paragraph("Listado de Procesos Judiciales - GADP", estilos["Title"])]

    datos = [["Nº", "NUREJ", "Categoría", "Demandante", "Demandado", "Juzgado", "Estado"]]
    for p in procesos:
        activa = p.partes_activas.first()
        pasiva = p.partes_pasivas.first()
        datos.append([
            p.nro_correlativo,
            p.nurej or "-",
            p.categoria.nombre,
            (activa.parte.nombre if activa else "-")[:35],
            (pasiva.parte.nombre if pasiva else "-")[:35],
            p.juzgado.nombre[:30],
            p.estado_actual.nombre,
        ])

    tabla = Table(datos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c1917")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f8f6")]),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    return response