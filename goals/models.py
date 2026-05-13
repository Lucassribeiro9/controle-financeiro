"""Models do app goals."""

from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError

# Create your models here.


class Goal(models.Model):
    """Esse model representa um objetivo financeiro."""

    class GoalType(models.TextChoices):
        ACCUMULATION = "accumulation", "Acumulação"
        REDUCTION = "reduction", "Redução"

    name = models.CharField(max_length=255)
    goal_type = models.CharField(max_length=20, choices=GoalType.choices)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    start_date = models.DateField()
    target_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    accounts = models.ManyToManyField(
        "accounts.FinancialAccount", blank=True, related_name="goals"
    )
    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="goals",
    )

    def clean(self) -> None:
        super().clean()

        if self.target_amount <= Decimal("0.00"):
            raise ValidationError({"target_amount": "O valor alvo deve ser positivo."})
        if self.goal_type == self.GoalType.REDUCTION and not self.category:
            raise ValidationError(
                {"category": "Objetivos de redução devem ter categoria vinculada."}
            )
        if self.target_date and self.target_date <= self.start_date:
            raise ValidationError(
                {"target_date": "A data alvo deve ser posterior à data de início."}
            )

    class Meta:
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"

    def __str__(self) -> str:
        return self.name


class MonthlyGoal(models.Model):
    """Esse model representa um objetivo financeiro mensal."""

    class Status(models.TextChoices):
        ON_TRACK = "on_track", "No caminho"
        AT_RISK = "at_risk", "Em risco"
        ACHIEVED = "achieved", "Atingido"
        MISSED = "missed", "Não atingida"

    goal = models.ForeignKey(
        Goal, on_delete=models.CASCADE, related_name="monthly_goals"
    )
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    current_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ON_TRACK
    )

    def clean(self) -> None:
        super().clean()
        if self.target_amount <= Decimal("0.00"):
            raise ValidationError({"target_amount": "O valor alvo deve ser positivo."})
        if self.current_amount < Decimal("0.00"):
            raise ValidationError(
                {"current_amount": "O valor atual não pode ser negativo."}
            )
        if not (1 <= self.month <= 12):
            raise ValidationError({"month": "O mês deve estar entre 1 e 12."})
        if not self.goal:
            raise ValidationError(
                {"goal": "A meta mensal deve estar vinculada a um objetivo."}
            )

    class Meta:
        verbose_name = "Meta Mensal"
        verbose_name_plural = "Metas Mensais"
        unique_together = ("goal", "year", "month")

    def __str__(self) -> str:
        return f"{self.goal.name} - {self.year}-{self.month:02d}"
