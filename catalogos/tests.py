from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Perfil

CLAVE = "clave-de-prueba-123"


class GestionCatalogosPermisosTest(TestCase):
    """Solo el área jurídica (admin) o el administrador pueden gestionar
    catálogos; un abogado solo puede consultarlos... salvo que ni eso pueda,
    en cuyo caso esta prueba debería avisarlo."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_juridico = User.objects.create_user("admin_juridico", password=CLAVE)
        cls.admin_juridico.perfil.rol = Perfil.Rol.ADMIN
        cls.admin_juridico.perfil.save()

        cls.abogado = User.objects.create_user("abogado_uno", password=CLAVE)
        cls.abogado.perfil.rol = Perfil.Rol.ABOGADO
        cls.abogado.perfil.save()

    def test_abogado_no_puede_gestionar_catalogos(self):
        self.client.login(username="abogado_uno", password=CLAVE)
        resp = self.client.get(reverse("catalogos:lista", args=["categorias"]))
        self.assertEqual(resp.status_code, 403)

    def test_admin_juridico_si_puede_gestionar_catalogos(self):
        self.client.login(username="admin_juridico", password=CLAVE)
        resp = self.client.get(reverse("catalogos:lista", args=["categorias"]))
        self.assertEqual(resp.status_code, 200)
