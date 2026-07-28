from django import forms

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso
from catalogos.utils import normalizar_mayusculas
from common.mixins import BootstrapFormMixin


class CategoriaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "orden"]


class TipoProcesoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TipoProceso
        fields = ["categoria", "nombre"]

    def clean_nombre(self):
        nombre = normalizar_mayusculas(self.cleaned_data["nombre"])
        categoria = self.data.get("categoria")
        duplicado = TipoProceso.objects.filter(nombre__iexact=nombre, categoria_id=categoria)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError(
                f"Ya existe un tipo de proceso con ese nombre en esta categoría: «{duplicado.first().nombre}»."
            )
        return nombre


class JuzgadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Juzgado
        fields = ["nombre", "tipo"]

    def clean_nombre(self):
        nombre = normalizar_mayusculas(self.cleaned_data["nombre"])
        duplicado = Juzgado.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError(f"Ya existe un juzgado registrado con ese nombre: «{duplicado.first().nombre}».")
        return nombre


class EstadoProcesoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EstadoProceso
        fields = ["nombre", "orden", "es_final"]


class ParteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Parte
        fields = ["nombre", "tipo_persona"]

    def clean_nombre(self):
        nombre = normalizar_mayusculas(self.cleaned_data["nombre"])
        duplicado = Parte.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError(f"Ya existe una parte registrada con ese nombre: «{duplicado.first().nombre}».")
        return nombre