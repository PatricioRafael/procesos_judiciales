from django import forms

from catalogos.models import Categoria, EstadoProceso


class ProcesoForm(forms.Form):
    """
    Formulario "estilo Excel": el doctor escribe los datos con los mismos
    campos de su hoja de cálculo. Por dentro, la vista se encarga de
    convertir estos textos libres en registros normalizados (Juzgado,
    Parte, TipoProceso) sin duplicar los que ya existen.
    """

    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(), label="Categoría del proceso"
    )
    nurej = forms.CharField(label="NUREJ", max_length=50, required=False)

    # Texto libre, como en el Excel. La vista hace get_or_create.
    parte_activa = forms.CharField(
        label="Demandante", max_length=500,
        help_text="Si hay varios, sepáralos con coma."
    )
    parte_pasiva = forms.CharField(
        label="Demandado", max_length=500,
        help_text="Si hay varios, sepáralos con coma."
    )

    tipo_proceso = forms.CharField(label="Tipo de proceso", max_length=255, required=False)
    juzgado = forms.CharField(label="Juzgado", max_length=255)

    estado_actual = forms.ModelChoiceField(queryset=EstadoProceso.objects.all(), label="Estado actual")
    fecha_registro = forms.DateField(
        label="Fecha de la demanda/acción", required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    # Solo se usan si categoria == Contencioso (se muestran/ocultan con JS)
    proyecto = forms.CharField(label="Proyecto", max_length=500, required=False)
    nro_contrato = forms.CharField(label="Nº de contrato", max_length=100, required=False)
    fecha_contrato = forms.DateField(
        label="Fecha de contrato", required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )
    motivo_demanda = forms.CharField(
        label="Motivo de la demanda", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    observacion_inicial = forms.CharField(
        label="Resumen del estado", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Se guarda como la primera entrada del historial del proceso."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
        if categoria and categoria.nombre == "Contencioso":
            if not cleaned.get("nro_contrato") and not cleaned.get("proyecto"):
                self.add_error("nro_contrato", "Para procesos Contenciosos, indica al menos el proyecto o el contrato.")
            # En Contencioso el demandado siempre es el GADP; no se pide en el formulario.
            self.errors.pop("parte_pasiva", None)
        return cleaned
    
class HistorialEstadoForm(forms.ModelForm):
    class Meta:
        model = HistorialEstado
        fields = ["estado_nuevo", "fecha_modificacion", "observacion"]
        widgets = {
            "fecha_modificacion": forms.DateInput(attrs={"type": "date"}),
            "observacion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css


class AccionFuturaForm(forms.ModelForm):
    class Meta:
        model = AccionFutura
        fields = ["descripcion", "fecha_limite", "responsable", "completada"]
        widgets = {
            "fecha_limite": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css