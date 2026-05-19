"""Forms do app transactions."""

from django import forms

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category

from .models import Transaction


ALLOWED_TRANSACTION_TYPES = [
    Transaction.TransactionType.INCOME,
    Transaction.TransactionType.EXPENSE,
    Transaction.TransactionType.ADJUSTMENT,
    Transaction.TransactionType.CARD_PURCHASE,
]


class TransactionForm(forms.Form):
    """Form para criar lancamentos financeiros usando services."""

    description = forms.CharField(label="Descricao", max_length=255)
    amount = forms.DecimalField(label="Valor", max_digits=14, decimal_places=2)
    transaction_type = forms.ChoiceField(
        label="Tipo",
        choices=[
            choice
            for choice in Transaction.TransactionType.choices
            if choice[0] in ALLOWED_TRANSACTION_TYPES
        ],
    )
    status = forms.ChoiceField(
        label="Status",
        choices=[
            choice
            for choice in Transaction.PaymentStatus.choices
            if choice[0] != Transaction.PaymentStatus.FORECASTED
        ],
        initial=Transaction.PaymentStatus.PENDING,
    )
    account = forms.ModelChoiceField(
        label="Conta",
        queryset=FinancialAccount.objects.none(),
        required=False,
    )
    category = forms.ModelChoiceField(
        label="Categoria",
        queryset=Category.objects.none(),
        required=False,
    )
    card = forms.ModelChoiceField(
        label="Cartao",
        queryset=Card.objects.none(),
        required=False,
    )
    date = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    notes = forms.CharField(
        label="Observacoes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        """Configura querysets dos campos relacionais."""

        super().__init__(*args, **kwargs)

        self.fields["account"].queryset = FinancialAccount.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["card"].queryset = Card.objects.filter(
            is_active=True
        ).order_by("name")

    def clean_amount(self):
        """Valida que o valor informado e positivo."""

        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Valor deve ser maior que zero.")
        return amount

    def clean(self):
        """Aplica regras de campos obrigatorios por tipo de lancamento."""

        cleaned_data = super().clean()
        transaction_type = cleaned_data.get("transaction_type")
        account = cleaned_data.get("account")
        card = cleaned_data.get("card")

        if transaction_type == Transaction.TransactionType.CARD_PURCHASE:
            if card is None:
                self.add_error("card", "Compra no cartao exige cartao vinculado.")
        elif transaction_type in ALLOWED_TRANSACTION_TYPES and account is None:
            self.add_error("account", "Lancamento exige conta financeira.")

        return cleaned_data
