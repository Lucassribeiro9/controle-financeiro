"""Forms do app rates."""

from django import forms

from accounts.models import FinancialAccount

from .models import AccountYieldConfig, ReferenceRate


class ReferenceRateForm(forms.Form):
    """Formulario para cadastrar CDI anual manual."""

    date = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    value = forms.DecimalField(
        label="CDI anual em decimal, exemplo 0.1065",
        max_digits=18,
        decimal_places=8,
    )
    notes = forms.CharField(
        label="Observacoes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def clean_value(self):
        """Valida taxa positiva."""

        value = self.cleaned_data["value"]
        if value <= 0:
            raise forms.ValidationError("Valor da taxa deve ser maior que zero.")
        return value


class AccountYieldConfigForm(forms.ModelForm):
    """Formulario para configurar rendimento de uma conta."""

    class Meta:
        model = AccountYieldConfig
        fields = ["account", "yield_type", "cdi_percentage", "is_active"]
        labels = {
            "account": "Conta",
            "yield_type": "Tipo de rendimento",
            "cdi_percentage": "Percentual do CDI",
            "is_active": "Ativa",
        }
        widgets = {
            "cdi_percentage": forms.NumberInput(attrs={"step": "0.0001"}),
        }

    def __init__(self, *args, **kwargs):
        """Configura contas disponiveis para rendimento."""

        super().__init__(*args, **kwargs)
        accounts = FinancialAccount.objects.filter(is_active=True).order_by("name")
        if self.instance.pk:
            accounts = accounts | FinancialAccount.objects.filter(
                pk=self.instance.account_id
            )
        self.fields["account"].queryset = accounts.distinct()

    def clean_account(self):
        """Impede mais de uma configuracao por conta."""

        account = self.cleaned_data["account"]
        duplicate_configs = AccountYieldConfig.objects.filter(account=account)
        if self.instance.pk:
            duplicate_configs = duplicate_configs.exclude(pk=self.instance.pk)

        if duplicate_configs.exists():
            raise forms.ValidationError(
                "Esta conta ja possui configuracao de rendimento."
            )

        return account


class YieldSimulationForm(forms.Form):
    """Formulario para simular rendimento de uma conta configurada."""

    account = forms.ModelChoiceField(
        label="Conta",
        queryset=FinancialAccount.objects.none(),
    )
    amount = forms.DecimalField(
        label="Valor inicial",
        max_digits=14,
        decimal_places=2,
    )
    months = forms.IntegerField(label="Meses", min_value=1)

    def __init__(self, *args, **kwargs):
        """Lista apenas contas com configuracao ativa."""

        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = (
            FinancialAccount.objects.filter(
                yield_config__is_active=True,
            )
            .select_related("institution")
            .order_by("name")
        )
