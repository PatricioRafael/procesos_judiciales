from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from catalogos.forms import CategoriaForm, EstadoProcesoForm, JuzgadoForm, ParteForm, TipoProcesoForm
from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from usuarios.models import es_admin_juridico

CATALOGOS = {
    "categorias": {"model": Categoria, "form": CategoriaForm, "titulo": "Categorías", "select_related": None},
    "tipos-proceso": {"model": TipoProceso, "form": TipoProcesoForm, "titulo": "Tipos de proceso", "select_related": "categoria"},
    "juzgados": {"model": Juzgado, "form": JuzgadoForm, "titulo": "Juzgados", "select_related": None},
    "estados": {"model": EstadoProceso, "form": EstadoProcesoForm, "titulo": "Estados de proceso", "select_related": None},
    "partes": {"model": Parte, "form": ParteForm, "titulo": "Partes procesales", "select_related": None},
}


class SoloAdminJuridicoMixin(UserPassesTestMixin):
    def test_func(self):
        return es_admin_juridico(self.request.user)

    def handle_no_permission(self):
        raise PermissionDenied("Solo el área jurídica o el superadmin pueden gestionar catálogos.")


class CatalogoListView(LoginRequiredMixin, SoloAdminJuridicoMixin, View):
    def get(self, request, slug):
        config = CATALOGOS.get(slug)
        if not config:
            from django.http import Http404
            raise Http404
        qs = config["model"].objects.all()
        if config["select_related"]:
            qs = qs.select_related(config["select_related"])
        return render(request, "catalogos/lista.html", {
            "objetos": qs, "slug": slug, "titulo": config["titulo"], "catalogos": CATALOGOS,
        })


class CatalogoCreateView(LoginRequiredMixin, SoloAdminJuridicoMixin, View):
    def get(self, request, slug):
        config = CATALOGOS[slug]
        return render(request, "catalogos/formulario.html", {
            "form": config["form"](), "slug": slug, "titulo": config["titulo"], "modo": "crear",
        })

    def post(self, request, slug):
        config = CATALOGOS[slug]
        form = config["form"](request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['titulo']}: registro creado correctamente.")
            return redirect("catalogos:lista", slug=slug)
        return render(request, "catalogos/formulario.html", {
            "form": form, "slug": slug, "titulo": config["titulo"], "modo": "crear",
        })


class CatalogoUpdateView(LoginRequiredMixin, SoloAdminJuridicoMixin, View):
    def get(self, request, slug, pk):
        config = CATALOGOS[slug]
        objeto = get_object_or_404(config["model"], pk=pk)
        return render(request, "catalogos/formulario.html", {
            "form": config["form"](instance=objeto), "slug": slug, "titulo": config["titulo"], "modo": "editar",
        })

    def post(self, request, slug, pk):
        config = CATALOGOS[slug]
        objeto = get_object_or_404(config["model"], pk=pk)
        form = config["form"](request.POST, instance=objeto)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['titulo']}: registro actualizado.")
            return redirect("catalogos:lista", slug=slug)
        return render(request, "catalogos/formulario.html", {
            "form": form, "slug": slug, "titulo": config["titulo"], "modo": "editar",
        })