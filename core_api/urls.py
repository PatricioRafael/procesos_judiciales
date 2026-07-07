from rest_framework.routers import DefaultRouter

from core_api.viewsets import (
    AbogadoViewSet,
    AccionFuturaViewSet,
    CategoriaViewSet,
    DocumentoProcesoViewSet,
    EstadoProcesoViewSet,
    HistorialEstadoViewSet,
    JuzgadoViewSet,
    ParteViewSet,
    ProcesoViewSet,
    TipoProcesoViewSet,
)

router = DefaultRouter()
router.register("categorias", CategoriaViewSet)
router.register("tipos-proceso", TipoProcesoViewSet)
router.register("juzgados", JuzgadoViewSet)
router.register("estados-proceso", EstadoProcesoViewSet)
router.register("partes", ParteViewSet)
router.register("abogados", AbogadoViewSet, basename="abogado")
router.register("procesos", ProcesoViewSet, basename="proceso")
router.register("historial", HistorialEstadoViewSet, basename="historial")
router.register("acciones-futuras", AccionFuturaViewSet, basename="accion-futura")
router.register("documentos", DocumentoProcesoViewSet, basename="documento")

urlpatterns = router.urls