from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

class Transaction(models.Model):
    """Representa uma transacao financeira manual, importada ou prevista."""

    class TransactionType(models.TextChoices):
        """Lista os tipos de transacao suportados no cadastro inicial."""

        INCOME = "income", "Receita"
        EXPENSE = "expense", "Despesa"
        ADJUSTMENT = "adjustment", "Ajuste"
        CARD_PURCHASE = "card_purchase", "Compra no cartão"
        BENEFIT_PURCHASE = "benefit_purchase", "Compra no benefício"
        FORECAST = "forecast", "Previsão"
        STATEMENT_PAYMENT = "statement_payment", "Pagamento de fatura"

    class PaymentStatus(models.TextChoices):
        """Lista os status de pagamento usados em lancamentos e previsoes."""

        FORECASTED = "forecasted", "Previsto"
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        PARTIALLY_PAID = "partially_paid", "Pago parcial"
        LATE = "late", "Atrasado"
        CANCELED = "canceled", "Cancelado"
        IGNORED = "ignored", "Ignorado"

    description = models.CharField("Descrição", max_length=255)
    amount = models.DecimalField(
        "Valor",
        max_digits=14,
        decimal_places=2,
    )
    transaction_type = models.CharField(
        "Tipo",
        max_length=20,
        choices=TransactionType.choices,
    )
    status = models.CharField(
        "Status",
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    account = models.ForeignKey(
        "accounts.FinancialAccount",
        verbose_name="Conta financeira",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
    )
    category = models.ForeignKey(
        "categories.Category",
        verbose_name="Categoria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    card = models.ForeignKey(
        "cards.Card",
        verbose_name="Cartão de crédito",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    date = models.DateField("Data da transação")
    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    # fatura do cartao associada (para compras no cartao, pode ser diferente da fatura atual do cartao para permitir flexibilidade)
    statement = models.ForeignKey(
        "cards.CardStatement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    installment_plan = models.ForeignKey(
        "installments.InstallmentPlan",
        verbose_name="Plano de parcelamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    installment_number = models.PositiveIntegerField(
        "Número da parcela",
        null=True,
        blank=True,
    )

    class Meta:
        """Define metadados de exibicao, ordenacao e unicidade."""

        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        ordering = ["-date", "-created_at"]

    def clean(self):
        """Aplica regras minimas para manter a transacao consistente."""

        super().clean()

        if self.amount is not None and self.amount <= Decimal("0"):
            raise ValidationError({"amount": "Valor deve ser maior que zero."})

        if self.transaction_type == self.TransactionType.CARD_PURCHASE:
            if self.card is None:
                raise ValidationError({"card": "Compra no cartão exige cartão vinculado."})
            if self.card.card_type != "credit":
                raise ValidationError({"card": "Compra no cartão exige cartão de crédito."})

        if self.transaction_type == self.TransactionType.BENEFIT_PURCHASE:
            if self.card is None:
                raise ValidationError({"card": "Compra no benefício exige cartão vinculado."})
            if self.card.card_type != "benefit":
                raise ValidationError({"card": "Compra no benefício exige cartão de benefício."})

        if self.transaction_type not in (
            self.TransactionType.CARD_PURCHASE,
            self.TransactionType.BENEFIT_PURCHASE,
        ) and self.account is None:
            raise ValidationError({"account": "Transação exige conta financeira."})

        if self.statement_id and self.transaction_type not in (
            self.TransactionType.CARD_PURCHASE,
            self.TransactionType.STATEMENT_PAYMENT,
        ):
            raise ValidationError(
                {"statement": "Apenas compras no cartão ou pagamentos de fatura podem ter fatura vinculada."}
            )

        if self.statement_id and self.card_id and self.statement.card_id != self.card_id:
            raise ValidationError({"statement": "Fatura deve pertencer ao cartão da transação."})

        if self.installment_plan_id:
            if self.transaction_type != self.TransactionType.CARD_PURCHASE:
                raise ValidationError(
                    {
                        "installment_plan": "Parcelamento exige transação de compra no cartão."
                    }
                )
            if self.card_id and self.installment_plan.card_id != self.card_id:
                raise ValidationError(
                    {"installment_plan": "Parcelamento deve pertencer ao cartão da transação."}
                )
            if self.installment_number is None:
                raise ValidationError(
                    {"installment_number": "Parcela exige número da parcela."}
                )
            if self.installment_number > self.installment_plan.total_installments:
                raise ValidationError(
                    {"installment_number": "Número da parcela excede o total do plano."}
                )

    def __str__(self) -> str:
        """Retorna uma descricao curta para exibicao no admin e logs."""

        return f"{self.description} - {self.amount}"


class Transfer(models.Model):
    """Representa uma transferencia entre contas financeiras."""

    description = models.CharField("Descrição", max_length=255)
    amount = models.DecimalField(
        "Valor",
        max_digits=14,
        decimal_places=2,
    )
    from_account = models.ForeignKey(
        "accounts.FinancialAccount",
        verbose_name="Conta de origem",
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    destination_account = models.ForeignKey(
        "accounts.FinancialAccount",
        verbose_name="Conta de destino",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    date = models.DateField("Data da transferência")
    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    
    class Meta:
        """Define metadados de exibicao, ordenacao e unicidade."""

        verbose_name = "Transferência"
        verbose_name_plural = "Transferências"
        ordering = ["-date", "-created_at"]

    def clean(self):
        """Aplica regras minimas para transferencia interna."""

        super().clean()

        if self.amount is not None and self.amount <= Decimal("0"):
            raise ValidationError({"amount": "Valor deve ser maior que zero."})

        if self.from_account_id and self.from_account_id == self.destination_account_id:
            raise ValidationError(
                {"destination_account": "Conta de destino deve ser diferente da conta de origem."}
            )

    def __str__(self) -> str:
        """Retorna uma descricao curta para exibicao no admin e logs."""

        return f"{self.from_account} -> {self.destination_account} - {self.amount}"
