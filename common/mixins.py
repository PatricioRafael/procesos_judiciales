from django import forms


def aplicar_clases_bootstrap(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            css = "form-check-input"
        elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            css = "form-select"
        else:
            css = "form-control"
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{existing} {css}".strip()


class BootstrapFormMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_clases_bootstrap(self)


class JuridicoAdminPermissionMixin:

    def has_module_permission(self, request):
        return request.user.is_superuser or (
            hasattr(request.user, "perfil") and request.user.perfil.es_admin_juridico
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
