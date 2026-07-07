from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import FormView

from catalogos.models import Juzgado, Parte, TipoProceso
from procesos.forms import ProcesoForm
from procesos.models import DetalleContrato, HistorialEstado, Proceso, ProcesoParte
from usuarios.models import es_admin_juridico, es_abogado


def _dividir_nombres(texto):
    """'Juan Pérez, María Gómez' -> ['Juan Pérez', 'María Gómez']"""
    return [n.strip() for n in texto.split(",") if n.strip()]


class ProcesoCreateView(LoginRequiredMixin, FormView):
    form_class = ProcesoForm
    template_name = "procesos/formulario.html"

    def form_valid(self, form):
        datos = form.cleaned_data
        user = self.request.user

        # 1. Juzgado: texto libre -> busca o crea en el catálogo
        juzgado, _ = Juzgado.objects.get_or_create(nombre=datos["juzgado"].strip())

        # 2. Tipo de proceso: texto libre -> busca o crea, ligado a la categoría
        tipo_proceso = None
        if datos.get("tipo_proceso"):
            tipo_proceso, _ = TipoProceso.objects.get_or_create(
                categoria=datos["categoria"], nombre=datos["tipo_proceso"].strip()
            )

        # 3. Crear el proceso
        ultimo = Proceso.objects.filter(categoria=datos["categoria"]).count()
        siguiente_nro = str(ultimo + 1)
        proceso = Proceso.objects.create(
            nro_correlativo=siguiente_nro,
            nurej=datos.get("nurej") or None,
            categoria=datos["categoria"],
            tipo_proceso=tipo_proceso,
            juzgado=juzgado,
            estado_actual=datos["estado_actual"],
            fecha_registro=datos.get("fecha_registro"),
            abogado_responsable=user if es_abogado(user) else None,
        )

        # 4. Partes: texto libre separado por comas -> busca o crea cada una
        for nombre in _dividir_nombres(datos["parte_activa"]):
            parte, _ = Parte.objects.get_or_create(nombre=nombre)
            ProcesoParte.objects.create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.ACTIVA)

        if datos["categoria"].nombre == "Contencioso":
            parte, _ = Parte.objects.get_or_create(nombre="Gobierno Autónomo Departamental de Potosí")
            ProcesoParte.objects.create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.PASIVA)
        else:
            for nombre in _dividir_nombres(datos.get("parte_pasiva", "")):
                parte, _ = Parte.objects.get_or_create(nombre=nombre)
                ProcesoParte.objects.create(proceso=proceso, parte=parte, rol=ProcesoParte.Rol.PASIVA)

        # 5. Detalle de contrato, solo si es Contencioso
        if datos["categoria"].nombre == "Contencioso":
            DetalleContrato.objects.create(
                proceso=proceso,
                proyecto=datos.get("proyecto", ""),
                nro_contrato=datos.get("nro_contrato", ""),
                fecha_contrato=datos.get("fecha_contrato"),
                motivo_demanda=datos.get("motivo_demanda", ""),
            )

        # 6. Primera entrada del historial (si escribió algo)
        if datos.get("observacion_inicial"):
            HistorialEstado.objects.create(
                proceso=proceso,
                estado_nuevo=datos["estado_actual"],
                usuario=user,
                observacion=datos["observacion_inicial"],
            )

        # 7. Documentos del paso 4 (si subió alguno)
        from procesos.models import DocumentoProceso
        for archivo in self.request.FILES.getlist("documentos"):
            DocumentoProceso.objects.create(
                proceso=proceso, archivo=archivo, subido_por=user, descripcion=archivo.name
            )

        messages.success(self.request, f"Proceso Nº {proceso.nro_correlativo} registrado correctamente.")
        self.proceso_creado = proceso
        return redirect("procesos:detalle", pk=proceso.pk)
    
from django.views.generic import DetailView, ListView

from catalogos.models import Categoria, EstadoProceso


class ProcesoListView(LoginRequiredMixin, ListView):
    model = Proceso
    template_name = "procesos/listado.html"
    context_object_name = "procesos"
    paginate_by = 25

    def get_queryset(self):
        qs = Proceso.objects.select_related(
            "categoria", "juzgado", "estado_actual", "abogado_responsable"
        ).order_by("-actualizado_en")

        categoria = self.request.GET.get("categoria")
        estado = self.request.GET.get("estado")
        q = self.request.GET.get("q")
        mios = self.request.GET.get("mios")

        if categoria:
            qs = qs.filter(categoria_id=categoria)
        if estado:
            qs = qs.filter(estado_actual_id=estado)
        if q:
            qs = qs.filter(nro_correlativo__icontains=q) | qs.filter(nurej__icontains=q)
        if mios and es_abogado(self.request.user):
            qs = qs.filter(abogado_responsable=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorias"] = Categoria.objects.all()
        ctx["estados"] = EstadoProceso.objects.all()

        todos = Proceso.objects.all()
        ctx["total_activos"] = todos.filter(activo=True).count()
        ctx["casos_apelacion"] = todos.filter(estado_actual__nombre__icontains="apelación").count()
        ctx["procesos_concluidos"] = todos.filter(estado_actual__es_final=True).count()

        from procesos.models import AccionFutura
        ctx["tareas_pendientes"] = AccionFutura.objects.filter(completada=False).count()

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

    def form_valid(self, form):
        messages.success(self.request, "Proceso actualizado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


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