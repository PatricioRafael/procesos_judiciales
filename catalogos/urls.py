from django.urls import path

from catalogos import views

app_name = "catalogos"

urlpatterns = [
    path("<str:slug>/", views.CatalogoListView.as_view(), name="lista"),
    path("<str:slug>/nuevo/", views.CatalogoCreateView.as_view(), name="crear"),
    path("<str:slug>/<int:pk>/editar/", views.CatalogoUpdateView.as_view(), name="editar"),
]