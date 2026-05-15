"""Models para o app insights."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.


class Insight(models.Model):
    """Modelo para armazenar insights."""

    class InsightType(models.TextChoices):
        RECURRING_EXPENSE = "recurring_expense", "Despesa Recorrente"
        CATEGORY_LIMIT = "category_limit", "Limite de Categoria"
        MONTHLY_GOAL = "monthly_goal", "Meta Mensal"
        BILL_REMINDER = "bill_reminder", "Lembrete de Conta"
        LOW_BALANCE = "low_balance", "Saldo Baixo"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovado"
        IGNORED = "ignored", "Ignorado"
        SILENCED = "silenced", "Silenciado"

    title = models.CharField(max_length=255)
    message = models.TextField()
    insight_type = models.CharField(max_length=50, choices=InsightType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    suggested_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    category = models.ForeignKey(
        "categories.Category", on_delete=models.SET_NULL, null=True, blank=True
    )
    recurrence = models.ForeignKey(
        "recurrences.Recurrence", on_delete=models.SET_NULL, null=True, blank=True
    )
    monthly_goal = models.ForeignKey(
        "goals.MonthlyGoal", on_delete=models.SET_NULL, null=True, blank=True
    )

    source_key = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Configurações do modelo Insight."""

        ordering = ["-title", "-created_at"]
        verbose_name = "Insight"
        verbose_name_plural = "Insights"

    def clean(self):
        """Regras de validação para o modelo Insight."""
        super().clean()

        if self.insight_type == self.InsightType.CATEGORY_LIMIT and not self.category:
            raise ValidationError(
                {
                    "category": "A categoria é obrigatória para insights do tipo 'Limite de Categoria'."
                }
            )
        if self.suggested_amount is not None and self.suggested_amount <= Decimal("0.00"):
            raise ValidationError(
                {"suggested_amount": "O valor sugerido deve ser maior que zero."}
            )

    def __str__(self):
        """Representação em string do modelo Insight."""
        return f"{self.title} ({self.get_insight_type_display()})"


class IgnoredPattern(models.Model):
    """Modelo para armazenar padrões de insights ignorados, evitando sugestões repetitivas."""

    pattern_key = models.CharField(max_length=120, unique=True)
    reason = models.TextField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configurações do modelo IgnoredPattern."""

        ordering = ["-created_at"]
        verbose_name = "Padrão Ignorado"
        verbose_name_plural = "Padrões Ignorados"

    def __str__(self):
        """Representação em string do modelo IgnoredPattern."""
        return self.pattern_key
