from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from procesos.models import AccionFutura, DocumentoProceso, Evento, HistorialEstado, Proceso
from usuarios.auditoria import registrar


@receiver(post_save, sender=Proceso)
def auditar_proceso_guardado(sender, instance, created, **kwargs):
    accion = "Creado Proceso" if created else "Editado Proceso"
    registrar(accion, modulo=instance.categoria.nombre if instance.categoria_id else "Procesos", detalle={
        "id": instance.id,
        "nro_correlativo": instance.nro_correlativo,
        "nurej": instance.nurej,
    })


@receiver(post_delete, sender=Proceso)
def auditar_proceso_borrado(sender, instance, **kwargs):
    registrar("Eliminado Proceso", modulo="Procesos", detalle={"id": instance.id, "nurej": instance.nurej})


@receiver(post_save, sender=HistorialEstado)
def auditar_historial(sender, instance, created, **kwargs):
    if created:
        registrar("Nueva actuación", modulo="Historial", detalle={
            "proceso_id": instance.proceso_id, "estado_nuevo": instance.estado_nuevo.nombre,
        })


@receiver(post_save, sender=AccionFutura)
def auditar_accion_futura(sender, instance, created, **kwargs):
    accion = "Creada acción futura" if created else "Editada acción futura"
    registrar(accion, modulo="Acciones Futuras", detalle={"proceso_id": instance.proceso_id, "descripcion": instance.descripcion[:80]})


@receiver(post_save, sender=DocumentoProceso)
def auditar_documento(sender, instance, created, **kwargs):
    if created:
        registrar("Documento subido", modulo="Gestión Documental", detalle={
            "proceso_id": instance.proceso_id, "archivo": instance.archivo.name,
        })


@receiver(post_delete, sender=DocumentoProceso)
def auditar_documento_borrado(sender, instance, **kwargs):
    registrar("Eliminación Documento", modulo="Gestión Documental", detalle={"proceso_id": instance.proceso_id})


@receiver(post_save, sender=Evento)
def auditar_evento(sender, instance, created, **kwargs):
    if created:
        registrar("Evento creado", modulo="Calendario", detalle={"titulo": instance.titulo, "fecha": str(instance.fecha)})