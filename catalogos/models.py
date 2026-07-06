from django.db import models


class Categoria(models.Model):

    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class TipoProceso(models.Model):

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="tipos_proceso")
    nombre = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Tipo de proceso"
        verbose_name_plural = "Tipos de proceso"
        unique_together = ("categoria", "nombre")
        ordering = ["categoria", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"


class Juzgado(models.Model):

    class Tipo(models.TextChoices):
        JUZGADO = "JUZGADO", "Juzgado"
        SALA = "SALA", "Sala"
        TRIBUNAL = "TRIBUNAL", "Tribunal"
        OTRO = "OTRO", "Otro"

    nombre = models.CharField(max_length=255, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.JUZGADO)

    class Meta:
        verbose_name = "Juzgado"
        verbose_name_plural = "Juzgados"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class EstadoProceso(models.Model):

    nombre = models.CharField(max_length=150, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)
    es_final = models.BooleanField(default=False, help_text="Marca estados que cierran el proceso")

    class Meta:
        verbose_name = "Estado de proceso"
        verbose_name_plural = "Estados de proceso"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Parte(models.Model):

    class TipoPersona(models.TextChoices):
        NATURAL = "NATURAL", "Persona natural"
        JURIDICA = "JURIDICA", "Persona juridica"

    nombre = models.CharField(max_length=500)
    tipo_persona = models.CharField(max_length=10, choices=TipoPersona.choices, default=TipoPersona.NATURAL)
    nro_documento = models.CharField(max_length=50, blank=True, help_text="CI o NIT, si se conoce")

    class Meta:
        verbose_name = "Parte procesal"
        verbose_name_plural = "Partes procesales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre