"""Forms do app installments."""

from django import forms

from cards.models import Card
from categories.models import Category
from core.forms import BRDateField
from core.forms import BRDecimalField
from core.forms import BRIntegerField


class InstallmentPlanForm(forms.Form):
    """Formulario para criar parcelamentos."""

    description = forms.CharField(label="Descrição", max_length=255)
    total_amount = BRDecimalField(
        label="Valor total",
        max_digits=14,
        decimal_places=2,
    )
    total_installments = BRIntegerField(label="Total de parcelas", min_value=1)
    first_installment_date = BRDateField(label="Data da primeira parcela")
    card = forms.ModelChoiceField(
        label="Cartão",
        queryset=Card.objects.none(),
    )
    category = forms.ModelChoiceField(
        label="Categoria",
        queryset=Category.objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        """Configura querysets de cartoes e categorias."""

        super().__init__(*args, **kwargs)
        self.fields["card"].queryset = (
            Card.objects.filter(is_active=True, card_type=Card.CardType.CREDIT)
            .select_related("institution")
            .order_by("name")
        )
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        ).order_by("name")

    def clean_total_amount(self):
        """Valida valor total positivo."""

        total_amount = self.cleaned_data["total_amount"]
        if total_amount <= 0:
            raise forms.ValidationError("Valor total deve ser maior que zero.")
        return total_amount
