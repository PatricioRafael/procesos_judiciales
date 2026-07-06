from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalogos.models import Categoria, EstadoProceso

CATEGORIAS = [
    "Contencioso",
    "Civil",
    "Agroambiental",
    "Coactivo social",
    "Laboral",
    "Constitucional",
    "Coactivo fiscal",
]

ESTADOS = [
    ("En trámite", False),
    ("Con responde", False),
    ("En etapa probatoria", False),
    ("Para auto de relación procesal", False),
    ("En ejecución de sentencia", False),
    ("Con recurso de apelación", False),
    ("Con recurso de casación", False),
    ("En fase de calificación", False),
    ("Concluido", True),
    ("Archivado", True),
]


class Command(BaseCommand):
    help = "Crea las categorías y estados base del sistema (idempotente)."

    def handle(self, *args, **options):
        for orden, nombre in enumerate(CATEGORIAS):
            obj, creado = Categoria.objects.get_or_create(
                nombre=nombre, defaults={"slug": slugify(nombre), "orden": orden}
            )
            self.stdout.write(("Creada" if creado else "Ya existía") + f": categoría {obj}")

        for orden, (nombre, es_final) in enumerate(ESTADOS):
            obj, creado = EstadoProceso.objects.get_or_create(
                nombre=nombre, defaults={"orden": orden, "es_final": es_final}
            )
            self.stdout.write(("Creado" if creado else "Ya existía") + f": estado {obj}")

        self.stdout.write(self.style.SUCCESS("Catálogos base listos."))