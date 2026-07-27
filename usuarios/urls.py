from django.urls import path

from usuarios import views

app_name = "usuarios"

urlpatterns = [
    path("", views.UsuarioListView.as_view(), name="lista"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/resetear-password/", views.ResetearPasswordView.as_view(), name="resetear_password"),
    path("<int:pk>/toggle-activo/", views.ToggleActivoView.as_view(), name="toggle_activo"),
    path("auditoria/", views.AuditoriaListView.as_view(), name="auditoria"),
    path("auditoria/exportar/", views.exportar_auditoria_csv, name="auditoria_csv"),
]