"""Forms do app transactions."""

from django import forms
from django.db.models import Q

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from core.forms import BRDateField
from core.forms import BRDecimalField
from core.forms import BRIntegerField

from .models import Transaction


TYPE_INCOME = "income"
TYPE_EXPENSE = "expense"
TYPE_TRANSFER = "transfer"

TYPE_CHOICES = [
    (TYPE_INCOME, "Receita"),
    (TYPE_EXPENSE, "Despesa"),
    (TYPE_TRANSFER, "Transferência"),
]

SOURCE_GROUP_ACCOUNTS = "Contas"
SOURCE_GROUP_CREDIT = "Cartões de crédito"
SOURCE_GROUP_BALANCE = "Cartões de saldo"

KIND_ACCOUNT = "account"
KIND_CREDIT = "credit"
KIND_BALANCE = "balance"


class SourceSelect(forms.Select):
    """Select de origem que marca cada opcao com o tipo (conta, credito, saldo)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kinds = {}

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        kind = self.kinds.get(value)
        if kind:
            option["attrs"]["data-kind"] = kind
        return option


class TransactionForm(forms.Form):
    """Form de lancamento: tipo e origem unica; a forma de pagamento deriva da origem (ADR-015)."""

    description = forms.CharField(label="Descrição", max_length=255)
    transaction_type = forms.ChoiceField(
        label="Tipo",
        choices=TYPE_CHOICES,
        initial=TYPE_EXPENSE,
    )
    source = forms.ChoiceField(
        label="Pagar com / Receber em",
        required=False,
        widget=SourceSelect,
    )
    amount = BRDecimalField(label="Valor", max_digits=14, decimal_places=2)
    status = forms.ChoiceField(
        label="Status",
        choices=[
            choice
            for choice in Transaction.PaymentStatus.choices
            if choice[0] != Transaction.PaymentStatus.FORECASTED
        ],
        initial=Transaction.PaymentStatus.PENDING,
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
        """Configura querysets e as opcoes agrupadas da origem."""

        self.allow_transfer = kwargs.pop("allow_transfer", True)
        self.transaction = kwargs.pop("transaction", None)
        super().__init__(*args, **kwargs)

        accounts = FinancialAccount.objects.filter(is_active=True).order_by("name")
        self.fields["from_account"].queryset = accounts
        self.fields["destination_account"].queryset = accounts
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        ).order_by("name")

        if not self.allow_transfer:
            self.fields["transaction_type"].choices = [
                choice for choice in TYPE_CHOICES if choice[0] != TYPE_TRANSFER
            ]

        self._configure_source_field()
        self.fields["transaction_type"].widget.attrs.update(
            {"data-conditional-source": "transaction-type"}
        )
        self.fields["source"].widget.attrs.update(
            {
                "data-conditional-field": "payment-source",
                "data-label-income": "Receber em",
                "data-label-expense": "Pagar com",
            }
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

    def _configure_source_field(self):
        """Monta o select unico de origem com grupos de contas e cartoes."""

        saved_account_id = self.transaction.account_id if self.transaction else None
        saved_card_id = self.transaction.card_id if self.transaction else None

        accounts = (
            FinancialAccount.objects.filter(
                Q(is_active=True) | Q(pk=saved_account_id)
            )
            .select_related("institution")
            .order_by("name")
        )
        cards = Card.objects.filter(
            Q(is_active=True) | Q(pk=saved_card_id)
        ).order_by("name")

        kinds = {}
        account_options = []
        for account in accounts:
            value = f"account:{account.pk}"
            kinds[value] = KIND_ACCOUNT
            account_options.append((value, str(account)))

        credit_options = []
        balance_options = []
        for card in cards:
            value = f"card:{card.pk}"
            label = f"{card.name} ({card.get_card_type_display().lower()})"
            if card.card_type == Card.CardType.CREDIT:
                kinds[value] = KIND_CREDIT
                credit_options.append((value, label))
            elif card.is_balance_card:
                kinds[value] = KIND_BALANCE
                balance_options.append((value, label))

        choices = [("", "---------")]
        for group_label, options in (
            (SOURCE_GROUP_ACCOUNTS, account_options),
            (SOURCE_GROUP_CREDIT, credit_options),
            (SOURCE_GROUP_BALANCE, balance_options),
        ):
            if options:
                choices.append((group_label, options))

        self.fields["source"].choices = choices
        self.fields["source"].widget.kinds = kinds
        self._source_objects = {
            **{f"account:{account.pk}": account for account in accounts},
            **{f"card:{card.pk}": card for card in cards},
        }

    @classmethod
    def from_transaction(cls, transaction):
        """Cria um form inicializado a partir de uma transacao existente."""

        if transaction.transaction_type == Transaction.TransactionType.INCOME:
            form_type = TYPE_INCOME
        else:
            form_type = TYPE_EXPENSE

        if transaction.card_id:
            source = f"card:{transaction.card_id}"
        elif transaction.account_id:
            source = f"account:{transaction.account_id}"
        else:
            source = ""

        return cls(
            allow_transfer=False,
            transaction=transaction,
            initial={
                "description": transaction.description,
                "amount": transaction.amount,
                "transaction_type": form_type,
                "source": source,
                "status": transaction.status,
                "category": transaction.category,
                "total_installments": (
                    transaction.installment_plan.total_installments
                    if transaction.installment_plan_id
                    else None
                ),
                "date": transaction.date,
                "notes": transaction.notes,
            },
        )

    def clean_amount(self):
        """Valida que o valor informado e positivo."""

        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Valor deve ser maior que zero.")
        return amount

    def clean(self):
        """Deriva forma de pagamento, tipo, conta e cartao da origem escolhida."""

        cleaned_data = super().clean()
        form_type = cleaned_data.get("transaction_type")
        if form_type is None:
            return cleaned_data

        if form_type == TYPE_TRANSFER:
            return self._clean_transfer(cleaned_data)

        source = cleaned_data.get("source")
        if "source" in self.errors:
            return cleaned_data
        if not source:
            message = (
                "Selecione a conta que recebe o dinheiro."
                if form_type == TYPE_INCOME
                else "Selecione de onde sai o dinheiro."
            )
            self.add_error("source", message)
            return cleaned_data

        origin = self._source_objects.get(source)
        total_installments = cleaned_data.get("total_installments")
        is_account = isinstance(origin, FinancialAccount)
        is_credit = isinstance(origin, Card) and origin.card_type == Card.CardType.CREDIT

        if form_type == TYPE_INCOME:
            if not is_account:
                self.add_error("source", "Receita só pode ser recebida em uma conta.")
                return cleaned_data
            payment_method = "debit"
            transaction_type = Transaction.TransactionType.INCOME
        elif is_account:
            payment_method = "debit"
            transaction_type = Transaction.TransactionType.EXPENSE
        elif is_credit:
            payment_method = "credit"
            transaction_type = Transaction.TransactionType.CARD_PURCHASE
        else:
            payment_method = "benefit"
            transaction_type = Transaction.TransactionType.BENEFIT_PURCHASE

        if is_credit:
            if total_installments is not None and total_installments <= 1:
                self.add_error(
                    "total_installments",
                    "Parcela inválida deve ter ao menos 2 parcelas.",
                )
        elif total_installments:
            self.add_error(
                "total_installments",
                "Parcelamento só pode ser usado em compras no crédito.",
            )

        cleaned_data["payment_method"] = payment_method
        cleaned_data["transaction_type"] = transaction_type
        cleaned_data["account"] = origin if is_account else None
        cleaned_data["card"] = None if is_account else origin
        return cleaned_data

    def _clean_transfer(self, cleaned_data):
        """Valida contas de origem e destino de uma transferencia."""

        from_account = cleaned_data.get("from_account")
        destination_account = cleaned_data.get("destination_account")

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

        cleaned_data["payment_method"] = "transfer"
        cleaned_data["account"] = None
        cleaned_data["card"] = None
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
