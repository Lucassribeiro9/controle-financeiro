"""Forms do app transactions."""

from django import forms

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from core.forms import BRDateField
from core.forms import BRDecimalField
from core.forms import BRIntegerField

from .models import Transaction


ALLOWED_TRANSACTION_TYPES = [
    Transaction.TransactionType.INCOME,
    Transaction.TransactionType.EXPENSE,
    Transaction.TransactionType.ADJUSTMENT,
    Transaction.TransactionType.CARD_PURCHASE,
]

PAYMENT_METHODS = [
    ("debit", "Débito"),
    ("credit", "Crédito"),
    ("benefit", "Benefício"),
    ("cash", "Dinheiro/outro"),
    ("transfer", "Transferência"),
]


class TransactionForm(forms.Form):
    """Form para criar lancamentos financeiros usando services."""

    description = forms.CharField(label="Descrição", max_length=255)
    payment_method = forms.ChoiceField(
        label="Forma de pagamento",
        choices=PAYMENT_METHODS,
    )
    amount = BRDecimalField(label="Valor", max_digits=14, decimal_places=2)
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
    from_account = forms.ModelChoiceField(
        label="Conta origem",
        queryset=FinancialAccount.objects.none(),
        required=False,
    )
    destination_account = forms.ModelChoiceField(
        label="Conta destino",
        queryset=FinancialAccount.objects.none(),
        required=False,
    )
    category = forms.ModelChoiceField(
        label="Categoria",
        queryset=Category.objects.none(),
        required=False,
    )
    card = forms.ModelChoiceField(
        label="Cartão",
        queryset=Card.objects.none(),
        required=False,
    )
    total_installments = BRIntegerField(
        label="Total de parcelas",
        required=False,
        min_value=1,
    )
    date = BRDateField(label="Data")
    notes = forms.CharField(
        label="Observações",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        """Configura querysets dos campos relacionais."""

        super().__init__(*args, **kwargs)

        self.fields["account"].queryset = FinancialAccount.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["from_account"].queryset = FinancialAccount.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["destination_account"].queryset = FinancialAccount.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["card"].queryset = Card.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["transaction_type"].widget.attrs.update(
            {"data-conditional-source": "transaction-type"}
        )
        self.fields["payment_method"].widget.attrs.update(
            {"data-conditional-source": "payment-method"}
        )
        self.fields["account"].widget.attrs.update(
            {"data-conditional-field": "payment-account"}
        )
        self.fields["card"].widget.attrs.update(
            {"data-conditional-field": "payment-card"}
        )
        self.fields["total_installments"].widget.attrs.update(
            {"data-conditional-field": "payment-installments"}
        )
        self.fields["from_account"].widget.attrs.update(
            {"data-conditional-field": "payment-transfer"}
        )
        self.fields["destination_account"].widget.attrs.update(
            {"data-conditional-field": "payment-transfer"}
        )

    @classmethod
    def from_transaction(cls, transaction):
        """Cria um form inicializado a partir de uma transacao existente."""

        if transaction.transaction_type == Transaction.TransactionType.CARD_PURCHASE:
            payment_method = (
                "benefit"
                if transaction.card and transaction.card.card_type == Card.CardType.BENEFIT
                else "credit"
            )
        elif transaction.transaction_type == Transaction.TransactionType.INCOME:
            payment_method = "debit"
        elif transaction.transaction_type == Transaction.TransactionType.EXPENSE:
            payment_method = "debit"
        else:
            payment_method = "cash"

        return cls(
            initial={
                "description": transaction.description,
                "payment_method": payment_method,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type,
                "status": transaction.status,
                "account": transaction.account,
                "from_account": None,
                "destination_account": None,
                "category": transaction.category,
                "card": transaction.card,
                "total_installments": (
                    transaction.installment_plan.total_installments
                    if transaction.installment_plan_id
                    else None
                ),
                "date": transaction.date,
                "notes": transaction.notes,
            }
        )

    def clean_amount(self):
        """Valida que o valor informado e positivo."""

        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Valor deve ser maior que zero.")
        return amount

    def clean(self):
        """Aplica regras de campos obrigatorios por tipo de lancamento."""

        cleaned_data = super().clean()
        payment_method = cleaned_data.get("payment_method")
        transaction_type = cleaned_data.get("transaction_type")
        account = cleaned_data.get("account")
        card = cleaned_data.get("card")
        total_installments = cleaned_data.get("total_installments")
        from_account = cleaned_data.get("from_account")
        destination_account = cleaned_data.get("destination_account")

        if payment_method == "transfer":
            if from_account is None:
                self.add_error("from_account", "Transferência exige conta origem.")
            if destination_account is None:
                self.add_error("destination_account", "Transferência exige conta destino.")
            if (
                from_account is not None
                and destination_account is not None
                and from_account == destination_account
            ):
                self.add_error(
                    "destination_account",
                    "Conta de destino deve ser diferente da conta de origem.",
                )
            return cleaned_data

        if payment_method == "credit":
            if card is None:
                self.add_error("card", "Compra no cartão exige cartão vinculado.")
            if transaction_type != Transaction.TransactionType.CARD_PURCHASE:
                self.add_error(
                    "transaction_type",
                    "Crédito deve ser lançado como compra no cartão.",
                )
            if total_installments is not None and total_installments <= 1:
                self.add_error(
                    "total_installments",
                    "Parcela inválida deve ter ao menos 2 parcelas.",
                )
        elif payment_method == "benefit":
            if card is None:
                self.add_error("card", "Benefício exige cartão vinculado.")
            elif card.card_type != Card.CardType.BENEFIT:
                self.add_error("card", "Benefício exige cartão de benefício.")
            if transaction_type != Transaction.TransactionType.CARD_PURCHASE:
                self.add_error(
                    "transaction_type",
                    "Benefício deve ser lançado como compra no cartão.",
                )
        else:
            if account is None:
                self.add_error("account", "Lançamento exige conta financeira.")

        if payment_method == "credit" and card is not None and card.card_type != Card.CardType.CREDIT:
            self.add_error("card", "Crédito exige cartão de crédito.")

        if payment_method != "credit" and total_installments:
            self.add_error(
                "total_installments",
                "Parcelamento só pode ser usado em compras no crédito.",
            )

        return cleaned_data


class TransferForm(forms.Form):
    """Form para criar transferencias entre contas usando services."""

    description = forms.CharField(label="Descrição", max_length=255)
    amount = BRDecimalField(label="Valor", max_digits=14, decimal_places=2)
    from_account = forms.ModelChoiceField(
        label="Conta origem",
        queryset=FinancialAccount.objects.none(),
    )
    destination_account = forms.ModelChoiceField(
        label="Conta destino",
        queryset=FinancialAccount.objects.none(),
    )
    date = BRDateField(label="Data")
    notes = forms.CharField(
        label="Observações",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        """Configura querysets de contas ativas."""

        super().__init__(*args, **kwargs)

        accounts = FinancialAccount.objects.filter(is_active=True).order_by("name")
        self.fields["from_account"].queryset = accounts
        self.fields["destination_account"].queryset = accounts

    def clean_amount(self):
        """Valida que o valor informado e positivo."""

        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Valor deve ser maior que zero.")
        return amount

    def clean(self):
        """Valida que origem e destino sao contas diferentes."""

        cleaned_data = super().clean()
        from_account = cleaned_data.get("from_account")
        destination_account = cleaned_data.get("destination_account")

        if (
            from_account is not None
            and destination_account is not None
            and from_account == destination_account
        ):
            self.add_error(
                "destination_account",
                "Conta de destino deve ser diferente da conta de origem.",
            )

        return cleaned_data
