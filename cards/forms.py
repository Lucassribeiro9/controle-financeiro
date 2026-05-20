"""Forms do app cards."""

from django import forms

from accounts.models import FinancialAccount
from institutions.models import Institution

from .models import Card


class CardForm(forms.ModelForm):
    """Formulario para cadastrar e editar cartoes."""

    class Meta:
        model = Card
        fields = [
            "name",
            "institution",
            "card_type",
            "credit_limit",
            "statement_closing_day",
            "statement_due_day",
            "payment_account",
            "estimated_balance",
            "is_active",
        ]
        widgets = {
            "credit_limit": forms.NumberInput(attrs={"step": "0.01"}),
            "estimated_balance": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {
            "name": "Nome",
            "institution": "Instituicao",
            "card_type": "Tipo",
            "credit_limit": "Limite",
            "statement_closing_day": "Dia de fechamento",
            "statement_due_day": "Dia de vencimento",
            "payment_account": "Conta padrao de pagamento",
            "estimated_balance": "Saldo estimado",
            "is_active": "Ativo",
        }

    def __init__(self, *args, **kwargs):
        """Configura querysets dos campos relacionais."""

        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.order_by("name")
        self.fields["payment_account"].queryset = (
            FinancialAccount.objects.filter(is_active=True)
            .select_related("institution")
            .order_by("institution__name", "name")
        )

    def clean_name(self):
        """Normaliza espacos do nome."""

        return self.cleaned_data["name"].strip()

    def clean(self):
        """Valida unicidade de nome por instituicao com erro amigavel."""

        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        institution = cleaned_data.get("institution")

        if not name or institution is None:
            return cleaned_data

        duplicate_cards = Card.objects.filter(
            institution=institution,
            name__iexact=name,
        )
        if self.instance.pk:
            duplicate_cards = duplicate_cards.exclude(pk=self.instance.pk)

        if duplicate_cards.exists():
            self.add_error(
                "name",
                "Ja existe um cartao com este nome nesta instituicao.",
            )

        return cleaned_data


class StatementPaymentForm(forms.Form):
    """Formulario para pagar total ou parcialmente uma fatura."""

    amount = forms.DecimalField(
        label="Valor pago",
        max_digits=14,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"step": "0.01"}),
    )

    def __init__(self, *args, statement=None, **kwargs):
        """Recebe a fatura para validar o saldo restante."""

        super().__init__(*args, **kwargs)
        self.statement = statement

    def clean_amount(self):
        """Valida o valor informado quando houver pagamento parcial."""

        amount = self.cleaned_data["amount"]
        if amount is None:
            return amount

        if amount <= 0:
            raise forms.ValidationError("Valor de pagamento deve ser maior que zero.")

        if self.statement is not None:
            remaining_amount = self.statement.closed_amount - self.statement.paid_amount
            if amount > remaining_amount:
                raise forms.ValidationError(
                    "Valor de pagamento nao pode superar o saldo da fatura."
                )

        return amount
