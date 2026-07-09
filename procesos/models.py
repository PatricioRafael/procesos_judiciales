from django.conf import settings
from django.db import models
from django.urls import reverse

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso


class Proceso(models.Model):
    nro_correlativo = models.CharField(
        max_length=20, help_text="Correlativo dentro de su categoria, tal como en el Excel (Nº)"
    )
    nurej = models.CharField(max_length=50, blank=True, null=True, unique=True)

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="procesos")
    tipo_proceso = models.ForeignKey(
        TipoProceso, on_delete=models.PROTECT, related_name="procesos", null=True, blank=True
    )
    juzgado = models.ForeignKey(Juzgado, on_delete=models.PROTECT, related_name="procesos")
    estado_actual = models.ForeignKey(EstadoProceso, on_delete=models.PROTECT, related_name="procesos")

    abogado_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procesos_asignados",
    )
    abogado_referencia = models.CharField(
        max_length=255, blank=True,
        help_text="Nombre del profesional a cargo según el registro original (Excel), "
                   "por si aún no tiene una cuenta de usuario creada en el sistema."
    )

    fecha_registro = models.DateField(null=True, blank=True, help_text="Fecha de la demanda/acción, si se conoce")
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["categoria", "estado_actual"])]

    def __str__(self):
        return f"[{self.categoria.nombre} #{self.nro_correlativo}] {self.nurej or 's/n'}"

    def get_absolute_url(self):
        return reverse("procesos:detalle", args=[self.pk])

    @property
    def partes_activas(self):
        return self.partes.filter(rol=ProcesoParte.Rol.ACTIVA)

    @property
    def partes_pasivas(self):
        return self.partes.filter(rol=ProcesoParte.Rol.PASIVA)


class ProcesoParte(models.Model):

    class Rol(models.TextChoices):
        ACTIVA = "ACTIVA",
        PASIVA = "PASIVA",

    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, related_name="partes")
    parte = models.ForeignKey(Parte, on_delete=models.PROTECT, related_name="procesos")
    rol = models.CharField(max_length=10, choices=Rol.choices)

    class Meta:
        verbose_name = "Parte del proceso"
        verbose_name_plural = "Partes del proceso"
        unique_together = ("proceso", "parte", "rol")

    def __str__(self):
        return f"{self.parte.nombre} ({self.get_rol_display()})"


class DetalleContrato(models.Model):

    proceso = models.OneToOneField(Proceso, on_delete=models.CASCADE, primary_key=True, related_name="detalle_contrato")
    proyecto = models.CharField(max_length=500, blank=True)
    nro_contrato = models.CharField(max_length=100, blank=True)
    fecha_contrato = models.DateField(null=True, blank=True)
    motivo_demanda = models.TextField(blank=True)

    class Meta:
        verbose_name = "Detalle de contrato"
        verbose_name_plural = "Detalles de contrato"

    def __str__(self):
        return f"Contrato de {self.proceso}"


class HistorialEstado(models.Model):

    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.ForeignKey(
        EstadoProceso, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    estado_nuevo = models.ForeignKey(EstadoProceso, on_delete=models.PROTECT, related_name="+")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    fecha_modificacion = models.DateField(null=True, blank=True, help_text="Fecha del memorial/actuación, si se conoce")
    observacion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.proceso} -> {self.estado_nuevo} ({self.creado_en:%d/%m/%Y})"


class AccionFutura(models.Model):
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, related_name="acciones_futuras")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="acciones_asignadas"
    )
    descripcion = models.TextField()
    fecha_limite = models.DateField(null=True, blank=True)
    completada = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Acción futura"
        verbose_name_plural = "Acciones futuras"
        ordering = ["completada", "fecha_limite"]

    def __str__(self):
        return f"{self.descripcion[:60]} ({self.proceso})"


class DocumentoProceso(models.Model):
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, related_name="documentos")
    archivo = models.FileField(upload_to="procesos/%Y/%m/")
    descripcion = models.CharField(max_length=255, blank=True)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento del proceso"
        verbose_name_plural = "Documentos del proceso"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return self.descripcion or self.archivo.name
    
class Evento(models.Model):
    """Audiencias, vencimientos de plazo y recordatorios, opcionalmente
    ligados a un proceso."""

    class Tipo(models.TextChoices):
        AUDIENCIA = "AUDIENCIA", "Audiencia"
        VENCIMIENTO = "VENCIMIENTO", "Vencimiento de plazo"
        RECORDATORIO = "RECORDATORIO", "Recordatorio"

    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.RECORDATORIO)
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    proceso = models.ForeignKey(
        Proceso, on_delete=models.CASCADE, related_name="eventos", null=True, blank=True
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ["fecha", "hora"]

    def __str__(self):
        return f"{self.titulo} ({self.fecha})"