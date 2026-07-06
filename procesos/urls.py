from django.urls import path

from procesos import views

app_name = "procesos"

urlpatterns = [
    path("", views.ProcesoListView.as_view(), name="listado"),
    path("nuevo/", views.ProcesoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ProcesoDetailView.as_view(), name="detalle"),
]