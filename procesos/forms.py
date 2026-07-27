from django import forms

from catalogos.models import Categoria, EstadoProceso
from procesos.models import AccionFutura, Evento, HistorialEstado


class BootstrapFormMixin:
    """Agrega clases de Bootstrap a los widgets automáticamente."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
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

    fecha_registro = forms.DateField(
        label="Fecha de registro",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Fecha en que se registra el proceso en el sistema. Si la dejas vacía, se usa la fecha de hoy.",
    )

    estado_actual = forms.ModelChoiceField(queryset=EstadoProceso.objects.all(), label="Estado")
    estado_actual_texto = forms.CharField(
        label="Estado actual del proceso", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Descripción tal como se registra en el documento oficial."
    )

    profesional_a_cargo = forms.ModelChoiceField(
        label="Profesional a cargo",
        queryset=None,
        required=False,
        help_text="Selecciona al abogado responsable de este proceso.",
    )

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields["profesional_a_cargo"].queryset = User.objects.filter(
            perfil__rol__in=["ABOGADO", "ADMIN"], is_active=True
        ).order_by("first_name", "last_name")

        if usuario_actual and hasattr(usuario_actual, "perfil") and usuario_actual.perfil.rol == "ABOGADO":
            self.fields["profesional_a_cargo"].initial = usuario_actual.id

        from datetime import date
        self.fields["fecha_registro"].widget.attrs["max"] = date.today().isoformat()

    def _nombres_enviados(self, campo):
        """Recoge todos los valores enviados con el mismo nombre de campo
        (el formulario permite agregar varias filas para un mismo rol)."""
        if hasattr(self.data, "getlist"):
            valores = self.data.getlist(campo)
        else:
            valores = [self.data.get(campo, "")]
        return [v.strip() for v in valores if v and v.strip()]

    def clean_parte_activa(self):
        nombres = self._nombres_enviados("parte_activa")
        if not nombres:
            raise forms.ValidationError("Debes indicar al menos un demandante.")
        self.partes_activas_lista = nombres
        return nombres[0]

    def clean_parte_pasiva(self):
        nombres = self._nombres_enviados("parte_pasiva")
        self.partes_pasivas_lista = nombres
        return nombres[0] if nombres else ""

    def clean_nurej(self):
        nurej = self.cleaned_data.get("nurej", "").strip()
        if not nurej:
            return nurej
        from procesos.models import Proceso
        if Proceso.objects.filter(nurej=nurej).exists():
            raise forms.ValidationError("Ya existe un proceso registrado con este NUREJ.")
        return nurej

    def clean_fecha_registro(self):
        from datetime import date

        fecha = self.cleaned_data.get("fecha_registro")
        if fecha and fecha > date.today():
            raise forms.ValidationError("La fecha de registro no puede ser posterior a hoy.")
        return fecha

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
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
        fields = ["descripcion", "fecha_limite", "responsable"]
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