"""Forms do app rates."""

from django import forms

from accounts.models import FinancialAccount
from core.forms import AnnualRateField
from core.forms import BRDateField
from core.forms import BRDecimalField
from core.forms import BRIntegerField

from .models import AccountYieldConfig, ReferenceRate


class ReferenceRateForm(forms.Form):
    """Formulario para cadastrar CDI anual manual."""

    date = BRDateField(label="Data")
    value = AnnualRateField(
        label="CDI anual (%)",
        max_digits=18,
        decimal_places=8,
    )
    notes = forms.CharField(
        label="Observações",
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

    cdi_percentage = BRDecimalField(
        label="Percentual do CDI",
        max_digits=8,
        decimal_places=4,
        required=False,
    )

    class Meta:
        model = AccountYieldConfig
        fields = ["account", "yield_type", "cdi_percentage", "is_active"]
        labels = {
            "account": "Conta",
            "yield_type": "Tipo de rendimento",
            "is_active": "Ativa",
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
                "Esta conta já possui configuração de rendimento."
            )

        return account


class YieldSimulationForm(forms.Form):
    """Formulario para simular rendimento de uma conta configurada."""

    account = forms.ModelChoiceField(
        label="Conta",
        queryset=FinancialAccount.objects.none(),
    )
    amount = BRDecimalField(
        label="Valor inicial",
        max_digits=14,
        decimal_places=2,
    )
    months = BRIntegerField(label="Meses", min_value=1)

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
