from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from catalogos.utils import normalizar_mayusculas


class Command(BaseCommand):
    help = "Pasa a mayúsculas todos los campos de texto del sistema, fusionando duplicados donde aplique."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]

        with transaction.atomic():
            sp = transaction.savepoint()

            self._catalogos_simples(dry)
            self._partes(dry)
            self._juzgados(dry)
            self._tipos(dry)
            self._procesos(dry)
            self._textos_largos(dry)

            if dry:
                transaction.savepoint_rollback(sp)
                self.stdout.write(self.style.WARNING("\nDry-run: no se guardó nada."))
            else:
                transaction.savepoint_commit(sp)
                self.stdout.write(self.style.SUCCESS("\nTodo normalizado."))

    def _catalogos_simples(self, dry):
        for modelo, etiqueta in [(Categoria, "Categoría"), (EstadoProceso, "Estado")]:
            for obj in modelo.objects.all():
                nuevo = normalizar_mayusculas(obj.nombre)
                if obj.nombre != nuevo:
                    self.stdout.write(f"{etiqueta}: «{obj.nombre}» → «{nuevo}»")
                    if not dry:
                        obj.nombre = nuevo
                        obj.save(update_fields=["nombre"])

    def _partes(self, dry):
        from procesos.models import ProcesoParte

        vistos = {}
        for parte in Parte.objects.all().order_by("id"):
            nuevo = normalizar_mayusculas(parte.nombre)
            if nuevo in vistos:
                principal = vistos[nuevo]
                self.stdout.write(f"Parte duplicada: «{parte.nombre}» → fusiona con «{principal.nombre}»")
                if not dry:
                    for pp in ProcesoParte.objects.filter(parte=parte):
                        if ProcesoParte.objects.filter(proceso=pp.proceso, parte=principal, rol=pp.rol).exists():
                            pp.delete()
                        else:
                            pp.parte = principal
                            pp.save(update_fields=["parte"])
                    parte.delete()
            else:
                vistos[nuevo] = parte
                if parte.nombre != nuevo:
                    self.stdout.write(f"Parte: «{parte.nombre}» → «{nuevo}»")
                    if not dry:
                        parte.nombre = nuevo
                        parte.save(update_fields=["nombre"])

    def _juzgados(self, dry):
        from procesos.models import Proceso

        vistos = {}
        for juzgado in Juzgado.objects.all().order_by("id"):
            nuevo = normalizar_mayusculas(juzgado.nombre)
            if nuevo in vistos:
                principal = vistos[nuevo]
                self.stdout.write(f"Juzgado duplicado: «{juzgado.nombre}» → fusiona con «{principal.nombre}»")
                if not dry:
                    Proceso.objects.filter(juzgado=juzgado).update(juzgado=principal)
                    juzgado.delete()
            else:
                vistos[nuevo] = juzgado
                if juzgado.nombre != nuevo:
                    self.stdout.write(f"Juzgado: «{juzgado.nombre}» → «{nuevo}»")
                    if not dry:
                        juzgado.nombre = nuevo
                        juzgado.save(update_fields=["nombre"])

    def _tipos(self, dry):
        from procesos.models import Proceso

        vistos = {}
        for tipo in TipoProceso.objects.all().order_by("id"):
            nuevo = normalizar_mayusculas(tipo.nombre)
            clave = (tipo.categoria_id, nuevo)
            if clave in vistos:
                principal = vistos[clave]
                self.stdout.write(f"Tipo duplicado: «{tipo.nombre}» → fusiona con «{principal.nombre}»")
                if not dry:
                    Proceso.objects.filter(tipo_proceso=tipo).update(tipo_proceso=principal)
                    tipo.delete()
            else:
                vistos[clave] = tipo
                if tipo.nombre != nuevo:
                    self.stdout.write(f"Tipo: «{tipo.nombre}» → «{nuevo}»")
                    if not dry:
                        tipo.nombre = nuevo
                        tipo.save(update_fields=["nombre"])

    def _procesos(self, dry):
        from procesos.models import DetalleContrato, Proceso

        for p in Proceso.objects.all():
            nuevo_nurej = normalizar_mayusculas(p.nurej) if p.nurej else None
            if p.nurej != nuevo_nurej:
                self.stdout.write(f"NUREJ: «{p.nurej}» → «{nuevo_nurej}»")
                if not dry:
                    p.nurej = nuevo_nurej
                    p.save(update_fields=["nurej"])

        for d in DetalleContrato.objects.all():
            cambios = {}
            for campo in ["proyecto", "nro_contrato", "motivo_demanda"]:
                actual = getattr(d, campo)
                nuevo = normalizar_mayusculas(actual)
                if actual != nuevo:
                    cambios[campo] = nuevo
            if cambios:
                self.stdout.write(f"Detalle contrato del proceso {d.proceso_id}: {list(cambios.keys())}")
                if not dry:
                    for campo, valor in cambios.items():
                        setattr(d, campo, valor)
                    d.save(update_fields=list(cambios.keys()))

    def _textos_largos(self, dry):
        from procesos.models import AccionFutura, DocumentoProceso, Evento, HistorialEstado

        total = 0
        for h in HistorialEstado.objects.exclude(observacion=""):
            nuevo = normalizar_mayusculas(h.observacion)
            if h.observacion != nuevo:
                total += 1
                if not dry:
                    h.observacion = nuevo
                    h.save(update_fields=["observacion"])

        for a in AccionFutura.objects.all():
            nuevo = normalizar_mayusculas(a.descripcion)
            if a.descripcion != nuevo:
                total += 1
                if not dry:
                    a.descripcion = nuevo
                    a.save(update_fields=["descripcion"])

        for e in Evento.objects.all():
            cambios = {}
            for campo in ["titulo", "descripcion"]:
                actual = getattr(e, campo)
                nuevo = normalizar_mayusculas(actual)
                if actual != nuevo:
                    cambios[campo] = nuevo
            if cambios:
                total += 1
                if not dry:
                    for campo, valor in cambios.items():
                        setattr(e, campo, valor)
                    e.save(update_fields=list(cambios.keys()))

        for d in DocumentoProceso.objects.exclude(descripcion=""):
            nuevo = normalizar_mayusculas(d.descripcion)
            if d.descripcion != nuevo:
                total += 1
                if not dry:
                    d.descripcion = nuevo
                    d.save(update_fields=["descripcion"])

        self.stdout.write(f"Textos largos (observaciones, tareas, eventos, documentos): {total} registros")