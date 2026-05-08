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
        CARD_PURCHASE = "card_purchase", "Compra no cartao"
        FORECAST = "forecast", "Previsao"
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

    description = models.CharField("Descricao", max_length=255)
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
        verbose_name="Cartao de credito",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    date = models.DateField("Data da transacao")
    notes = models.TextField("Observacoes", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Define metadados de exibicao, ordenacao e unicidade."""

        verbose_name = "Transacao"
        verbose_name_plural = "Transacoes"
        ordering = ["-date", "-created_at"]

    def clean(self):
        """Aplica regras minimas para manter a transacao consistente."""

        super().clean()

        if self.amount is not None and self.amount <= Decimal("0"):
            raise ValidationError({"amount": "Valor deve ser maior que zero."})

        if self.transaction_type == self.TransactionType.CARD_PURCHASE and self.card is None:
            raise ValidationError({"card": "Compra no cartao exige cartao vinculado."})

        if self.transaction_type != self.TransactionType.CARD_PURCHASE and self.account is None:
            raise ValidationError({"account": "Transacao exige conta financeira."})

    def __str__(self) -> str:
        """Retorna uma descricao curta para exibicao no admin e logs."""

        return f"{self.description} - {self.amount}"


class Transfer(models.Model):
    """Representa uma transferencia entre contas financeiras."""

    description = models.CharField("Descricao", max_length=255)
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
    date = models.DateField("Data da transferencia")
    notes = models.TextField("Observacoes", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    
    class Meta:
        """Define metadados de exibicao, ordenacao e unicidade."""

        verbose_name = "Transferencia"
        verbose_name_plural = "Transferencias"
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
