from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from procesos.models import AccionFutura, DocumentoProceso, Evento, HistorialEstado, Proceso
from usuarios.auditoria import registrar


CAMPOS_AUDITADOS = {
    "nurej": "NUREJ",
    "juzgado": "Juzgado",
    "estado_actual": "Estado",
    "categoria": "Categoría",
    "tipo_proceso": "Tipo de proceso",
    "abogado_responsable": "Abogado a cargo",
    "fecha_registro": "Fecha de registro",
    "activo": "Activo",
}


@receiver(pre_save, sender=Proceso)
def guardar_estado_previo(sender, instance, **kwargs):
    """Antes de guardar, lee cómo estaba el registro en la base de datos
    para poder comparar después qué campos cambiaron."""
    if not instance.pk:
        instance._estado_previo = None
        return
    try:
        anterior = Proceso.objects.get(pk=instance.pk)
    except Proceso.DoesNotExist:
        instance._estado_previo = None
        return
    instance._estado_previo = {campo: getattr(anterior, campo) for campo in CAMPOS_AUDITADOS}


@receiver(post_save, sender=Proceso)
def auditar_proceso_guardado(sender, instance, created, **kwargs):
    modulo = instance.categoria.nombre if instance.categoria_id else "Procesos"

    if created:
        registrar("Creado Proceso", modulo=modulo, detalle={
            "proceso_id": instance.id,
            "nro_correlativo": instance.nro_correlativo,
            "nurej": instance.nurej,
        })
        return

    previo = getattr(instance, "_estado_previo", None)
    if not previo:
        return

    cambios = {}
    for campo, etiqueta in CAMPOS_AUDITADOS.items():
        valor_anterior = previo.get(campo)
        valor_nuevo = getattr(instance, campo)
        if valor_anterior != valor_nuevo:
            cambios[etiqueta] = {
                "antes": str(valor_anterior) if valor_anterior not in (None, "") else "(vacío)",
                "ahora": str(valor_nuevo) if valor_nuevo not in (None, "") else "(vacío)",
            }

    if not cambios:
        return  # se guardó pero nada relevante cambió, no vale la pena registrarlo

    registrar("Editado Proceso", modulo=modulo, detalle={
        "proceso_id": instance.id,
        "cambios": cambios,
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
        registrar("Evento creado", modulo="Calendario", detalle={
            "proceso_id": instance.proceso_id,
            "titulo": instance.titulo,
            "fecha": str(instance.fecha),
        })