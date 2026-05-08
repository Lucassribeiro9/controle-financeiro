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
                raise ValidationError({"credit_limit": "Cartao de credito exige limite."})
            if self.statement_closing_day is None:
                raise ValidationError(
                    {"statement_closing_day": "Cartao de credito exige dia de fechamento."}
                )
            if self.statement_due_day is None:
                raise ValidationError(
                    {"statement_due_day": "Cartao de credito exige dia de vencimento."}
                )
            if self.payment_account is None:
                raise ValidationError(
                    {"payment_account": "Cartao de credito exige conta padrao de pagamento."}
                )

        if self.card_type == self.CardType.BENEFIT and self.estimated_balance is None:
            raise ValidationError({"estimated_balance": "Cartao de beneficio exige saldo estimado."})

        if self.statement_closing_day is not None and not 1 <= self.statement_closing_day <= 31:
            raise ValidationError({"statement_closing_day": "Dia de fechamento deve estar entre 1 e 31."})

        if self.statement_due_day is not None and not 1 <= self.statement_due_day <= 31:
            raise ValidationError({"statement_due_day": "Dia de vencimento deve estar entre 1 e 31."})

        if self.credit_limit is not None and self.credit_limit < Decimal("0"):
            raise ValidationError({"credit_limit": "Limite nao pode ser negativo."})

        if self.estimated_balance is not None and self.estimated_balance < Decimal("0"):
            raise ValidationError({"estimated_balance": "Saldo estimado nao pode ser negativo."})

    def __str__(self) -> str:
        """Retorna o nome amigavel do cartao para exibicao."""

        return self.name
