from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Card(models.Model):
    """Representa cartoes de credito e cartoes de beneficio/saldo."""

    class CardType(models.TextChoices):
        """Define os tipos de cartao suportados no cadastro inicial."""

        CREDIT = "credit", "Credito"
        BENEFIT = "benefit", "Beneficio"
        TRANSPORT = "transport", "Transporte"
        PREPAID = "prepaid", "Pre-pago"

    name = models.CharField("Nome", max_length=120)
    institution = models.ForeignKey(
        "institutions.Institution",
        verbose_name="Instituicao",
        on_delete=models.PROTECT,
        related_name="cards",
    )
    card_type = models.CharField("Tipo", max_length=20, choices=CardType.choices)

    credit_limit = models.DecimalField(
        "Limite",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    statement_closing_day = models.PositiveSmallIntegerField(
        "Dia de fechamento",
        null=True,
        blank=True,
    )
    statement_due_day = models.PositiveSmallIntegerField(
        "Dia de vencimento",
        null=True,
        blank=True,
    )
    payment_account = models.ForeignKey(
        "accounts.FinancialAccount",
        verbose_name="Conta padrao de pagamento",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cards_as_payment_account",
    )

    estimated_balance = models.DecimalField(
        "Saldo estimado",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Define metadados de exibicao e restricao de unicidade."""

        verbose_name = "Cartao"
        verbose_name_plural = "Cartoes"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_card_name_per_institution",
            )
        ]

    def clean(self):
        """Aplica regras de negocio minimas por tipo de cartao."""

        super().clean()

        if self.card_type == self.CardType.CREDIT:
            if self.credit_limit is None:
                raise ValidationError(
                    {"credit_limit": "Cartao de credito exige limite."}
                )
            if self.statement_closing_day is None:
                raise ValidationError(
                    {
                        "statement_closing_day": "Cartao de credito exige dia de fechamento."
                    }
                )
            if self.statement_due_day is None:
                raise ValidationError(
                    {"statement_due_day": "Cartao de credito exige dia de vencimento."}
                )
            if self.payment_account is None:
                raise ValidationError(
                    {
                        "payment_account": "Cartao de credito exige conta padrao de pagamento."
                    }
                )
        


        if self.card_type == self.CardType.BENEFIT and self.estimated_balance is None:
            raise ValidationError(
                {"estimated_balance": "Cartao de beneficio exige saldo estimado."}
            )

        if (
            self.statement_closing_day is not None
            and not 1 <= self.statement_closing_day <= 31
        ):
            raise ValidationError(
                {"statement_closing_day": "Dia de fechamento deve estar entre 1 e 31."}
            )

        if self.statement_due_day is not None and not 1 <= self.statement_due_day <= 31:
            raise ValidationError(
                {"statement_due_day": "Dia de vencimento deve estar entre 1 e 31."}
            )

        if self.credit_limit is not None and self.credit_limit < Decimal("0"):
            raise ValidationError({"credit_limit": "Limite nao pode ser negativo."})

        if self.estimated_balance is not None and self.estimated_balance < Decimal("0"):
            raise ValidationError(
                {"estimated_balance": "Saldo estimado nao pode ser negativo."}
            )

    def __str__(self) -> str:
        """Retorna o nome amigavel do cartao para exibicao."""

        return self.name


class CardStatement(models.Model):
    """Representa a fatura mensal de um cartao de credito."""

    class StatementStatus(models.TextChoices):
        """Define os status possiveis de uma fatura."""

        FORECASTED = "forecasted", "Previsao"
        LATE = "late", "Atrasada"
        OPEN = "open", "Aberta"
        PENDING = "pending", "Pendente"
        PAID = "paid", "Paga"
        CANCELED = "canceled", "Cancelada"
        PARTIALLY_PAID = "partially_paid", "Parcialmente paga"

    card = models.ForeignKey(
        Card,
        verbose_name="Cartao",
        on_delete=models.CASCADE,
        related_name="statements",
    )
    year = models.PositiveSmallIntegerField("Ano")
    month = models.PositiveSmallIntegerField("Mes")
    closed_amount = models.DecimalField(
        "Valor fechado",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    expected_amount = models.DecimalField(
        "Valor esperado",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    paid_amount = models.DecimalField(
        "Valor pago",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    closing_date = models.DateField("Data de fechamento")
    due_date = models.DateField("Data de vencimento")
    status = models.CharField(
        "Status",
        max_length=20,
        choices=StatementStatus.choices,
        default=StatementStatus.OPEN,
    )
    payment_account = models.ForeignKey(
        "accounts.FinancialAccount",
        verbose_name="Conta de pagamento",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="card_statements_as_payment_account",
    )
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Define metadados de exibicao e restricao de unicidade."""

        verbose_name = "Fatura do cartao"
        verbose_name_plural = "Faturas do cartao"
        ordering = ["-year", "-month", "card"]
        constraints = [
            models.UniqueConstraint(
                fields=["card", "year", "month"],
                name="unique_card_statement_per_month",
            )
        ]

    def clean(self):
        """Aplica regras minimas para manter a fatura consistente."""

        super().clean()

        if self.month is not None and not 1 <= self.month <= 12:
            raise ValidationError({"month": "Mes deve estar entre 1 e 12."})

        if self.card_id and self.card.card_type != Card.CardType.CREDIT:
            raise ValidationError({"card": "Apenas cartoes de credito podem ter faturas."})

        if self.card_id and self.payment_account_id is None:
            self.payment_account = self.card.payment_account

        amount_fields = {
            "closed_amount": self.closed_amount,
            "expected_amount": self.expected_amount,
            "paid_amount": self.paid_amount,
        }
        for field_name, value in amount_fields.items():
            if value is not None and value < Decimal("0"):
                raise ValidationError({field_name: "Valor nao pode ser negativo."})

        if (
            self.closed_amount is not None
            and self.paid_amount is not None
            and self.closed_amount > Decimal("0")
            and self.paid_amount > self.closed_amount
        ):
            raise ValidationError({"paid_amount": "Valor pago nao pode superar o valor fechado."})

    def __str__(self) -> str:
        """Retorna uma descricao curta da fatura."""

        return f"{self.card} - {self.month:02d}/{self.year}"
