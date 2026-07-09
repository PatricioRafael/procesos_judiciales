from django.urls import path

from procesos import views

app_name = "procesos"

urlpatterns = [
    path("dashboard/", views.ProcesoDashboardView.as_view(), name="dashboard"),
    path("", views.ProcesoListView.as_view(), name="listado"),
    path("nuevo/", views.ProcesoCreateView.as_view(), name="crear"),
    path("calendario/", views.CalendarioView.as_view(), name="calendario"),
    path("calendario/nuevo/", views.AgregarEventoView.as_view(), name="agregar_evento"),
    path("documentos/", views.DocumentosGlobalView.as_view(), name="documentos"),
    path("exportar/excel/", views.exportar_excel, name="exportar_excel"),
    path("exportar/pdf/", views.exportar_pdf, name="exportar_pdf"),
    path("<int:pk>/", views.ProcesoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ProcesoUpdateView.as_view(), name="editar"),
    path("<int:pk>/historial/nuevo/", views.AgregarHistorialView.as_view(), name="agregar_historial"),
    path("<int:pk>/acciones/nueva/", views.AgregarAccionFuturaView.as_view(), name="agregar_accion"),
]