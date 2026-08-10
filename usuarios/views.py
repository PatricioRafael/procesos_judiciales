from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from usuarios.forms import ResetearPasswordForm, UsuarioCreateForm, UsuarioUpdateForm
from usuarios.models import Perfil, RegistroAuditoria


class SoloAdministradorMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Solo el administrador puede gestionar usuarios.")


class UsuarioListView(SoloAdministradorMixin, View):
    def get(self, request):
        filtro = request.GET.get("filtro", "todos")
        q = request.GET.get("q", "")

        usuarios = User.objects.select_related("perfil").exclude(is_superuser=True).order_by("first_name")
        if filtro == "abogados":
            usuarios = usuarios.filter(perfil__rol=Perfil.Rol.ABOGADO)
        elif filtro == "admin":
            usuarios = usuarios.filter(perfil__rol=Perfil.Rol.ADMIN)
        if q:
            usuarios = usuarios.filter(first_name__icontains=q) | usuarios.filter(last_name__icontains=q) | usuarios.filter(username__icontains=q)

        contexto = {
            "usuarios": usuarios,
            "filtro": filtro,
            "q": q,
            "total_usuarios": User.objects.count(),
            "activos_ahora": User.objects.filter(is_active=True).count(),
            "roles_definidos": len(Perfil.Rol.choices) + 1,  # + Administrador
            "ultima_auditoria": RegistroAuditoria.objects.first(),
            "actividad_reciente": RegistroAuditoria.objects.filter(modulo="User Management")[:5],
        }
        return render(request, "usuarios/lista.html", contexto)


class UsuarioCreateView(SoloAdministradorMixin, View):
    def get(self, request):
        return render(request, "usuarios/formulario.html", {"form": UsuarioCreateForm(), "modo": "crear"})

    def post(self, request):
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            user = User.objects.create_user(
                username=datos["username"], email=datos["email"],
                password=datos["password"], first_name=datos["first_name"], last_name=datos["last_name"],
            )
            user.is_staff = datos["rol"] == Perfil.Rol.ADMIN
            user.save(update_fields=["is_staff"])
            user.perfil.rol = datos["rol"]
            user.perfil.save()
            messages.success(request, f"Usuario {user.username} creado correctamente.")
            return redirect("usuarios:lista")
        return render(request, "usuarios/formulario.html", {"form": form, "modo": "crear"})


class UsuarioUpdateView(SoloAdministradorMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UsuarioUpdateForm(initial={
            "first_name": user.first_name, "last_name": user.last_name, "email": user.email,
            "rol": user.perfil.rol, "is_active": user.is_active,
        })
        return render(request, "usuarios/formulario.html", {"form": form, "modo": "editar", "usuario_editado": user})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UsuarioUpdateForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            user.first_name = datos["first_name"]
            user.last_name = datos["last_name"]
            user.email = datos["email"]
            user.is_active = datos["is_active"]
            user.is_staff = datos["rol"] == Perfil.Rol.ADMIN
            user.save()
            user.perfil.rol = datos["rol"]
            user.perfil.save()
            messages.success(request, f"Usuario {user.username} actualizado.")
            return redirect("usuarios:lista")
        return render(request, "usuarios/formulario.html", {"form": form, "modo": "editar", "usuario_editado": user})


class ResetearPasswordView(SoloAdministradorMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return render(request, "usuarios/resetear_password.html", {"form": ResetearPasswordForm(), "usuario_editado": user})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = ResetearPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, f"Contraseña de {user.username} restablecida.")
            return redirect("usuarios:lista")
        return render(request, "usuarios/resetear_password.html", {"form": form, "usuario_editado": user})


class ToggleActivoView(SoloAdministradorMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"Usuario {user.username} {'activado' if user.is_active else 'desactivado'}.")
        return redirect("usuarios:lista")


class AuditoriaListView(SoloAdministradorMixin, View):
    def get(self, request):
        qs = RegistroAuditoria.objects.select_related("usuario").all()

        usuario_id = request.GET.get("usuario")
        accion = request.GET.get("accion")
        desde = request.GET.get("desde")
        hasta = request.GET.get("hasta")

        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        if accion:
            qs = qs.filter(accion__icontains=accion)
        if desde:
            qs = qs.filter(creado_en__date__gte=desde)
        if hasta:
            qs = qs.filter(creado_en__date__lte=hasta)

        from django.core.paginator import Paginator
        paginator = Paginator(qs, 25)
        pagina = paginator.get_page(request.GET.get("page"))

        contexto = {
            "registros": pagina,
            "usuarios": User.objects.filter(
                id__in=RegistroAuditoria.objects.exclude(usuario__isnull=True).values_list("usuario_id", flat=True).distinct()
            ),
            "acciones_distintas": RegistroAuditoria.objects.order_by("accion").values_list("accion", flat=True).distinct(),
        }
        return render(request, "usuarios/auditoria.html", contexto)


def exportar_auditoria_csv(request):
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="auditoria.csv"'
    writer = csv.writer(response)
    writer.writerow(["Fecha", "Usuario", "Acción", "Módulo", "IP", "Estado", "Detalle"])
    for r in RegistroAuditoria.objects.all():
        writer.writerow([r.creado_en.strftime("%d/%m/%Y %H:%M"), r.usuario_texto, r.accion, r.modulo, r.ip_address or "", r.estado, r.detalle])
    return response


class LoginPersonalizadoView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        recordarme = self.request.POST.get("recordarme")
        if recordarme:
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        else:
            self.request.session.set_expiry(0)
        return super().form_valid(form)