from django import forms

from catalogos.models import Categoria, EstadoProceso, Juzgado, Parte, TipoProceso


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            field.widget.attrs["class"] = css


class CategoriaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "slug", "orden"]


class TipoProcesoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TipoProceso
        fields = ["categoria", "nombre"]


class JuzgadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Juzgado
        fields = ["nombre", "tipo"]


class EstadoProcesoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EstadoProceso
        fields = ["nombre", "orden", "es_final"]


class ParteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Parte
        fields = ["nombre", "tipo_persona", "nro_documento"]