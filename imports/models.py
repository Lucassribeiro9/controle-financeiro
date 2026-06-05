"""Models do app imports."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from transactions.models import Transaction


class ImportedTransaction(models.Model):
    """Representa uma transação importada aguardando revisão do usuário."""

    class Status(models.TextChoices):
        """Lista os status possíveis de uma transação importada."""

        PENDING = "pending", "Pendente"
        CONFIRMED = "confirmed", "Confirmada"
        DISCARDED = "discarded", "Descartada"
        DUPLICATE = "duplicate", "Duplicada"

    class SourceType(models.TextChoices):
        """Lista os formatos de arquivo suportados pela importação."""

        CSV = "csv", "CSV"
        OFX = "ofx", "OFX"
        XLSX = "xlsx", "XLSX"

    source_file_name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    raw_description = models.CharField(max_length=255)
    normalized_description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    suggested_account = models.ForeignKey(
        "accounts.FinancialAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    suggested_category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    suggested_transaction_type = models.CharField(
        max_length=20,
        choices=[
            (Transaction.TransactionType.INCOME, "Receita"),
            (Transaction.TransactionType.EXPENSE, "Despesa"),
        ],
        null=True,
        blank=True,
    )
    confirmed_transaction = models.ForeignKey(
        "transactions.Transaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    external_id = models.CharField(max_length=255, blank=True)
    import_hash = models.CharField(max_length=64, blank=True, db_index=True)
    review_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        """Aplica regras para manter o ciclo de revisão consistente."""

        super().clean()

        if self.amount is not None and self.amount <= Decimal("0.00"):
            raise ValidationError({"amount": "O valor da transação deve ser positivo."})

        if self.status == self.Status.CONFIRMED and not self.confirmed_transaction:
            raise ValidationError(
                {
                    "confirmed_transaction": "Transações confirmadas devem ter uma transação associada."
                }
            )
        if self.status != self.Status.CONFIRMED and self.confirmed_transaction:
            raise ValidationError(
                {
                    "confirmed_transaction": "Transações não confirmadas não podem ter uma transação associada."
                }
            )
        if self.status == self.Status.DUPLICATE and not (
            self.external_id or self.import_hash
        ):
            raise ValidationError(
                {
                    "external_id": "Transações duplicadas devem ter external_id ou import_hash para rastrear a origem."
                }
            )

    class Meta:
        """Define metadados de exibição, ordenação e índices."""

        verbose_name = "Transação Importada"
        verbose_name_plural = "Transações Importadas"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "date"]),
            models.Index(fields=["source_type", "source_file_name"]),
        ]

    def __str__(self) -> str:
        """Retorna uma descrição curta para admin e logs."""

        return f"{self.source_file_name} - {self.raw_description}"
