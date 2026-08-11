from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Perfil

CLAVE = "clave-de-prueba-123"


class GestionUsuariosPermisosTest(TestCase):
    """Solo el administrador (is_superuser) puede gestionar usuarios."""

    @classmethod
    def setUpTestData(cls):
        cls.administrador = User.objects.create_superuser("admin_sistema", password=CLAVE)
        cls.admin_juridico = User.objects.create_user("admin_juridico", password=CLAVE)
        cls.admin_juridico.perfil.rol = Perfil.Rol.ADMIN
        cls.admin_juridico.perfil.save()

    def test_admin_juridico_no_puede_gestionar_usuarios(self):
        self.client.login(username="admin_juridico", password=CLAVE)
        resp = self.client.get(reverse("usuarios:lista"))
        self.assertEqual(resp.status_code, 403)

    def test_administrador_si_puede_gestionar_usuarios(self):
        self.client.login(username="admin_sistema", password=CLAVE)
        resp = self.client.get(reverse("usuarios:lista"))
        self.assertEqual(resp.status_code, 200)
