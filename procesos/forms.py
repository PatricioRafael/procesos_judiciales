from django import forms

from catalogos.models import Categoria, EstadoProceso
from procesos.models import AccionFutura, Evento, HistorialEstado


class BootstrapFormMixin:
    """Agrega clases de Bootstrap a los widgets automáticamente."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) else "form-control"
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css}".strip()


class ProcesoForm(BootstrapFormMixin, forms.Form):
    """
    Formulario de una sola página, con exactamente las columnas del
    documento oficial de procesos judiciales: Demandante, Proyecto/Motivo,
    Demandado, Juzgado, NUREJ, Estado actual, Profesional a cargo.
    """

    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all(), label="Categoría del proceso")

    parte_activa = forms.CharField(label="Demandante", max_length=500)
    proyecto_motivo = forms.CharField(label="Proyecto / Motivo", max_length=500, required=False)
    parte_pasiva = forms.CharField(label="Demandado", max_length=500, required=False)
    juzgado = forms.CharField(label="Juzgado", max_length=255)

    nurej = forms.CharField(label="NUREJ", max_length=50, required=False)

    estado_actual = forms.ModelChoiceField(queryset=EstadoProceso.objects.all(), label="Estado")
    estado_actual_texto = forms.CharField(
        label="Estado actual del proceso", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Descripción tal como se registra en el documento oficial."
    )

    abogado_referencia = forms.CharField(label="Profesional a cargo", max_length=255, required=False)

    def clean_nurej(self):
        nurej = self.cleaned_data.get("nurej", "").strip()
        if not nurej:
            return nurej
        from procesos.models import Proceso
        if Proceso.objects.filter(nurej=nurej).exists():
            raise forms.ValidationError("Ya existe un proceso registrado con este NUREJ.")
        return nurej

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
        # En Contencioso el demandado siempre es el GADP, así que no es obligatorio escribirlo.
        if categoria and categoria.nombre != "Contencioso":
            if not cleaned.get("parte_pasiva"):
                self.add_error("parte_pasiva", "Este campo es obligatorio para esta categoría.")
        return cleaned


class HistorialEstadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = HistorialEstado
        fields = ["estado_nuevo", "fecha_modificacion", "observacion"]
        widgets = {
            "fecha_modificacion": forms.DateInput(attrs={"type": "date"}),
            "observacion": forms.Textarea(attrs={"rows": 4}),
        }


class AccionFuturaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AccionFutura
        fields = ["descripcion", "fecha_limite", "responsable", "completada"]
        widgets = {
            "fecha_limite": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

class EventoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Evento
        fields = ["titulo", "descripcion", "tipo", "fecha", "hora", "proceso"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "hora": forms.TimeInput(attrs={"type": "time"}),
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }