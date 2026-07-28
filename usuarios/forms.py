from django import forms
from django.contrib.auth.models import User

from common.mixins import BootstrapFormMixin
from usuarios.models import Perfil


class UsuarioCreateForm(BootstrapFormMixin, forms.Form):
    username = forms.CharField(label="Nombre de usuario", max_length=150)
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo electrónico", required=False)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    rol = forms.ChoiceField(label="Rol", choices=Perfil.Rol.choices)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username


class UsuarioUpdateForm(BootstrapFormMixin, forms.Form):
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo electrónico", required=False)
    rol = forms.ChoiceField(label="Rol", choices=Perfil.Rol.choices)
    is_active = forms.BooleanField(label="Usuario activo", required=False)


class ResetearPasswordForm(BootstrapFormMixin, forms.Form):
    password = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)