"""Models do app recurrences."""

from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.


class Recurrence(models.Model):
    """Representa uma recorrência financeira, como uma despesa mensal ou uma receita anual."""

    class Frequency(models.TextChoices):
        """Lista os tipos de frequência de recorrência suportados."""

        MONTHLY = "monthly", "Mensal"
        ANNUAL = "annual", "Anual"
        WEEKLY = "weekly", "Semanal"
        BIWEEKLY = "biweekly", "Quinzenal"
        QUARTERLY = "quarterly", "Trimestral"
        CUSTOM = "custom", "Personalizada"

    class RecurrenceType(models.TextChoices):
        """Lista os tipos de recorrência suportados."""

        INCOME = "income", "Receita"
        FIXED_BILL = "fixed_bill", "Despesa fixa"
        SUBSCRIPTION = "subscription", "Assinatura"
        OTHER = "other", "Outro"

    name = models.CharField(max_length=255)
    expected_day = models.PositiveIntegerField()
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    recurrence_type = models.CharField(max_length=20, choices=RecurrenceType.choices)
    expected_amount = models.DecimalField(max_digits=14, decimal_places=2)
    is_active = models.BooleanField(default=True)
    requires_confirmation = models.BooleanField(default=True)
    account = models.ForeignKey(
        "accounts.FinancialAccount",
        verbose_name="Conta financeira",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recurrences",
    )
    card = models.ForeignKey(
        "cards.Card",
        verbose_name="Cartão de crédito",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recurrences",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Recorrência"
        verbose_name_plural = "Recorrências"
        ordering = ["expected_day", "name", "recurrence_type"]

    def clean(self) -> None:
        """Valida os dados antes de salvar."""
        super().clean()

        if self.expected_day < 1 or self.expected_day > 31:
            raise ValidationError(
                {"expected_day": "O dia esperado deve ser entre 1 e 31."}
            )
        if self.expected_amount <= 0:
            raise ValidationError(
                {"expected_amount": "O valor esperado deve ser positivo."}
            )
        if self.recurrence_type == self.RecurrenceType.FIXED_BILL and not self.account:
            raise ValidationError(
                {
                    "account": "Recorrências do tipo 'Despesa fixa' devem ter uma conta associada."
                }
            )
        if self.recurrence_type == self.RecurrenceType.SUBSCRIPTION and not self.card:
            raise ValidationError(
                {
                    "card": "Recorrências do tipo 'Assinatura' devem ter um cartão associado."
                }
            )

    def __str__(self) -> str:
        return f"{self.name} ({self.get_recurrence_type_display()}, {self.get_frequency_display()}) - R$ {self.expected_amount}"
