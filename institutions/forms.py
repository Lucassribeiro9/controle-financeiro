"""Forms do app institutions."""

from django import forms

from .models import Institution


class InstitutionForm(forms.ModelForm):
    """Formulario para cadastrar e editar instituicoes financeiras."""

    class Meta:
        model = Institution
        fields = ["name", "official_name", "code", "is_active"]
        labels = {
            "name": "Nome",
            "official_name": "Razão social",
            "code": "Código",
            "is_active": "Ativa",
        }

    def clean_name(self):
        """Normaliza espacos do nome."""

        return self.cleaned_data["name"].strip()

    def clean_code(self):
        """Normaliza codigo vazio para NULL."""

        code = (self.cleaned_data.get("code") or "").strip()
        return code or None

    def clean(self):
        """Valida nome unico e codigo unico quando informado."""

        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        code = cleaned_data.get("code")

        if name:
            duplicate_names = Institution.objects.filter(name__iexact=name)
            if self.instance.pk:
                duplicate_names = duplicate_names.exclude(pk=self.instance.pk)

            if duplicate_names.exists():
                self.add_error("name", "Já existe uma instituição com este nome.")

        if code:
            duplicate_codes = Institution.objects.filter(code__iexact=code)
            if self.instance.pk:
                duplicate_codes = duplicate_codes.exclude(pk=self.instance.pk)

            if duplicate_codes.exists():
                self.add_error("code", "Já existe uma instituição com este código.")

        return cleaned_data
