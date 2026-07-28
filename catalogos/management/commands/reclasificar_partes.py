from django.core.management.base import BaseCommand

from catalogos.models import Parte
from catalogos.utils import detectar_tipo_persona


class Command(BaseCommand):
    help = "Revisa las partes existentes y corrige su tipo de persona según el nombre."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué cambiaría, sin guardar.")

    def handle(self, *args, **options):
        cambiadas = 0
        for parte in Parte.objects.all():
            detectado = detectar_tipo_persona(parte.nombre)
            if detectado != parte.tipo_persona:
                self.stdout.write(f"{parte.nombre}: {parte.get_tipo_persona_display()} → {detectado}")
                if not options["dry_run"]:
                    parte.tipo_persona = detectado
                    parte.save(update_fields=["tipo_persona"])
                cambiadas += 1

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry-run: {cambiadas} partes cambiarían. No se guardó nada."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{cambiadas} partes actualizadas."))