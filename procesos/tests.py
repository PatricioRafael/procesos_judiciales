from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogos.models import Categoria, EstadoProceso, Juzgado
from procesos.models import HistorialEstado, Proceso
from usuarios.models import Perfil

CLAVE = "clave-de-prueba-123"


class ProcesoSmokeTest(TestCase):
    """Pruebas de humo: no cubren cada caso, pero detectan si el flujo básico
    de un expediente (crear, ver, cambiar de estado, exportar, permisos por
    rol) se rompe por un cambio futuro."""

    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre="Contencioso", orden=1)
        cls.juzgado = Juzgado.objects.create(nombre="Juzgado Primero Civil")
        cls.estado_inicial = EstadoProceso.objects.create(nombre="En trámite", orden=1)
        cls.estado_final = EstadoProceso.objects.create(nombre="Concluido", orden=2, es_final=True)

        cls.admin = User.objects.create_user("admin_juridico", password=CLAVE)
        cls.admin.perfil.rol = Perfil.Rol.ADMIN
        cls.admin.perfil.save()

        cls.abogado = User.objects.create_user("abogado_uno", password=CLAVE)
        cls.abogado.perfil.rol = Perfil.Rol.ABOGADO
        cls.abogado.perfil.save()

        cls.otro_abogado = User.objects.create_user("abogado_dos", password=CLAVE)
        cls.otro_abogado.perfil.rol = Perfil.Rol.ABOGADO
        cls.otro_abogado.perfil.save()

        cls.proceso = Proceso.objects.create(
            nro_correlativo="1",
            categoria=cls.categoria,
            juzgado=cls.juzgado,
            estado_actual=cls.estado_inicial,
            abogado_responsable=cls.abogado,
        )

    def test_dashboard_requiere_login(self):
        resp = self.client.get(reverse("procesos:dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_abogado_ve_el_listado(self):
        self.client.login(username="abogado_uno", password=CLAVE)
        resp = self.client.get(reverse("procesos:listado"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.proceso.nro_correlativo)

    def test_abogado_no_puede_editar_proceso_ajeno(self):
        self.client.login(username="abogado_dos", password=CLAVE)
        resp = self.client.get(reverse("procesos:editar", args=[self.proceso.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_abogado_responsable_si_puede_editar(self):
        self.client.login(username="abogado_uno", password=CLAVE)
        resp = self.client.get(reverse("procesos:editar", args=[self.proceso.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_admin_juridico_crea_proceso(self):
        self.client.login(username="admin_juridico", password=CLAVE)
        resp = self.client.post(reverse("procesos:crear"), {
            "categoria": self.categoria.pk,
            "parte_activa": "Juan Perez",
            "parte_pasiva": "Maria Gomez",
            "juzgado": "Juzgado Segundo Civil",
            "estado_actual": self.estado_inicial.pk,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Proceso.objects.filter(nro_correlativo="2", categoria=self.categoria).exists()
        )

    def test_cambiar_estado_actualiza_el_proceso_y_deja_historial(self):
        self.client.login(username="abogado_uno", password=CLAVE)
        resp = self.client.post(
            reverse("procesos:agregar_historial", args=[self.proceso.pk]),
            {"estado_nuevo": self.estado_final.pk, "observacion": "Se resolvió el caso."},
        )
        self.assertEqual(resp.status_code, 302)
        self.proceso.refresh_from_db()
        self.assertEqual(self.proceso.estado_actual, self.estado_final)
        self.assertTrue(
            HistorialEstado.objects.filter(proceso=self.proceso, estado_nuevo=self.estado_final).exists()
        )

    def test_exportar_excel(self):
        self.client.login(username="admin_juridico", password=CLAVE)
        resp = self.client.get(reverse("procesos:exportar_excel"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_exportar_pdf_de_un_proceso(self):
        self.client.login(username="admin_juridico", password=CLAVE)
        resp = self.client.get(reverse("procesos:exportar_proceso_pdf", args=[self.proceso.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
