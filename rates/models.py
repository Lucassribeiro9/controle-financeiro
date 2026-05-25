"""Models do app rates."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class ReferenceRate(models.Model):
    """Representa uma taxa de referencia historica."""

    class RateType(models.TextChoices):
        """Tipos de taxa suportados."""

        CDI = "cdi", "CDI"

    class Periodicity(models.TextChoices):
        """Periodicidades suportadas."""

        ANNUAL = "annual", "Anual"

    rate_type = models.CharField("Tipo", max_length=20, choices=RateType.choices)
    date = models.DateField("Data")
    value = models.DecimalField("Valor", max_digits=18, decimal_places=8)
    periodicity = models.CharField(
        "Periodicidade",
        max_length=20,
        choices=Periodicity.choices,
        default=Periodicity.ANNUAL,
    )
    source = models.CharField("Fonte", max_length=80, default="manual")
    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Define ordenacao e unicidade para taxas historicas."""

        verbose_name = "Taxa de referência"
        verbose_name_plural = "Taxas de referência"
        ordering = ["-date", "rate_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["rate_type", "date", "periodicity"],
                name="unique_reference_rate_per_type_date_periodicity",
            )
        ]

    def clean(self):
        """Valida taxa de referencia dentro do escopo."""

        super().clean()

        if self.rate_type != self.RateType.CDI:
            raise ValidationError({"rate_type": "Apenas CDI é suportado."})

        if self.periodicity != self.Periodicity.ANNUAL:
            raise ValidationError(
                {"periodicity": "Apenas periodicidade anual é suportada."}
            )

        if self.value is not None and self.value <= Decimal("0"):
            raise ValidationError({"value": "Valor da taxa deve ser maior que zero."})

    def __str__(self) -> str:
        """Retorna descricao curta da taxa."""

        return f"{self.get_rate_type_display()} {self.date} - {self.value}"


class AccountYieldConfig(models.Model):
    """Configura rendimento estimado de uma conta financeira."""

    class YieldType(models.TextChoices):
        """Tipos de rendimento suportados."""

        NONE = "none", "Sem rendimento"
        CDI_PERCENTAGE = "cdi_percentage", "% do CDI"

    account = models.OneToOneField(
        "accounts.FinancialAccount",
        verbose_name="Conta",
        on_delete=models.CASCADE,
        related_name="yield_config",
    )
    yield_type = models.CharField("Tipo de rendimento", max_length=30, choices=YieldType.choices)
    cdi_percentage = models.DecimalField(
        "Percentual do CDI",
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Define ordenacao e nomes legiveis."""

        verbose_name = "Configuração de rendimento"
        verbose_name_plural = "Configurações de rendimento"
        ordering = ["account__name"]

    def clean(self):
        """Valida compatibilidade entre tipo de rendimento e percentual."""

        super().clean()

        if self.yield_type == self.YieldType.CDI_PERCENTAGE:
            if self.cdi_percentage is None:
                raise ValidationError(
                    {"cdi_percentage": "Percentual do CDI é obrigatório."}
                )
            if self.cdi_percentage <= Decimal("0"):
                raise ValidationError(
                    {"cdi_percentage": "Percentual do CDI deve ser maior que zero."}
                )

        if self.yield_type == self.YieldType.NONE and self.cdi_percentage is not None:
            raise ValidationError(
                {"cdi_percentage": "Contas sem rendimento não devem ter percentual do CDI."}
            )

    def __str__(self) -> str:
        """Retorna descricao curta da configuracao."""

        return f"{self.account} - {self.get_yield_type_display()}"
