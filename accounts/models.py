from django.db import models


class FinancialAccount(models.Model):
    """Representa conta, caixinha ou reserva que possui saldo financeiro."""

    class AccountType(models.TextChoices):
        """Lista os tipos de conta suportados no cadastro inicial."""

        CHECKING = "checking", "Conta corrente"
        SAVINGS = "savings", "Poupanca"
        PIGGY_BANK = "piggy_bank", "Porquinho"
        BENEFIT = "benefit", "Beneficio"
        GLOBAL = "global", "Conta global"
        CASH = "cash", "Dinheiro"
        INVESTMENT = "investment", "Investimento"

    class Currency(models.TextChoices):
        """Lista as moedas iniciais."""

        BRL = "BRL", "Real brasileiro"
        USD = "USD", "Dolar americano"

    name = models.CharField("Nome", max_length=120)
    institution = models.ForeignKey(
        "institutions.Institution",
        verbose_name="Instituicao",
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_type = models.CharField(
        "Tipo",
        max_length=20,
        choices=AccountType.choices,
    )
    currency = models.CharField(
        "Moeda",
        max_length=3,
        choices=Currency.choices,
        default=Currency.BRL,
    )
    balance = models.DecimalField(
        "Saldo atual",
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Define metadados de exibicao, ordenacao e unicidade."""

        verbose_name = "Conta financeira"
        verbose_name_plural = "Contas financeiras"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_account_name_per_institution",
            )
        ]

    def __str__(self) -> str:
        """Retorna um nome amigavel para exibicao em telas e admin."""

        return f"{self.name} ({self.institution.name})"
