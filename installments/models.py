from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class InstallmentPlan(models.Model):
    """Representa uma compra parcelada em cartao."""

    class Status(models.TextChoices):
        """Status possiveis para o plano de parcelamento."""

        ACTIVE = "active", "Ativo"
        COMPLETED = "completed", "Concluído"
        CANCELED = "canceled", "Cancelado"

    description = models.CharField("Descrição", max_length=255)
    total_amount = models.DecimalField(
        "Valor total",
        max_digits=14,
        decimal_places=2,
    )
    installment_amount = models.DecimalField(
        "Valor da parcela",
        max_digits=14,
        decimal_places=2,
    )
    total_installments = models.PositiveIntegerField("Total de parcelas")
    first_installment_date = models.DateField("Data da primeira parcela")
    card = models.ForeignKey(
        "cards.Card",
        verbose_name="Cartão",
        on_delete=models.PROTECT,
        related_name="installment_plans",
    )
    category = models.ForeignKey(
        "categories.Category",
        verbose_name="Categoria",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="installment_plans",
    )
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Parcelamento"
        verbose_name_plural = "Parcelamentos"
        ordering = ["status", "first_installment_date", "description"]

    def clean(self):
        """Aplica regras minimas do plano de parcelamento."""

        super().clean()

        if self.total_amount is not None and self.total_amount <= Decimal("0"):
            raise ValidationError({"total_amount": "Valor total deve ser maior que zero."})

        if (
            self.installment_amount is not None
            and self.installment_amount <= Decimal("0")
        ):
            raise ValidationError(
                {"installment_amount": "Valor da parcela deve ser maior que zero."}
            )

        if self.total_installments is not None and self.total_installments <= 0:
            raise ValidationError(
                {"total_installments": "Total de parcelas deve ser maior que zero."}
            )

        if self.card_id and self.card.card_type != self.card.CardType.CREDIT:
            raise ValidationError({"card": "Parcelamento exige cartão de crédito."})

    def __str__(self) -> str:
        """Retorna uma descricao curta do parcelamento."""

        return f"{self.description} ({self.total_installments}x)"
