"""Forms do app accounts."""

from django import forms

from institutions.models import Institution

from .models import FinancialAccount


class FinancialAccountForm(forms.ModelForm):
    """Formulario para cadastrar e editar contas financeiras."""

    class Meta:
        model = FinancialAccount
        fields = [
            "name",
            "institution",
            "account_type",
            "currency",
            "balance",
            "is_active",
        ]
        widgets = {
            "balance": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {
            "name": "Nome",
            "institution": "Instituicao",
            "account_type": "Tipo",
            "currency": "Moeda",
            "balance": "Saldo atual",
            "is_active": "Ativa",
        }

    def __init__(self, *args, **kwargs):
        """Configura querysets de campos relacionais."""

        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.order_by("name")

    def clean_name(self):
        """Normaliza espacos do nome."""

        return self.cleaned_data["name"].strip()

    def clean(self):
        """Valida unicidade de nome por instituicao."""

        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        institution = cleaned_data.get("institution")

        if not name or institution is None:
            return cleaned_data

        duplicate_accounts = FinancialAccount.objects.filter(
            institution=institution,
            name__iexact=name,
        )
        if self.instance.pk:
            duplicate_accounts = duplicate_accounts.exclude(pk=self.instance.pk)

        if duplicate_accounts.exists():
            self.add_error(
                "name",
                "Ja existe uma conta com este nome nesta instituicao.",
            )

        return cleaned_data
