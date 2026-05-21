"""Tests dos services do app rates."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from rates.models import AccountYieldConfig, ReferenceRate
from rates.services import (
    estimate_account_yield,
    get_latest_cdi_rate,
    save_reference_rate,
    simulate_cdi_yield,
)


class RateServiceTests(TestCase):
    """Garante operacoes de negocio para taxas manuais."""

    def test_save_reference_rate_creates_valid_manual_rate(self):
        """Deve salvar CDI manual validado."""

        rate = save_reference_rate(
            date=date(2026, 5, 1),
            value=Decimal("0.10650000"),
            notes="CDI informado manualmente",
        )

        self.assertEqual(rate.rate_type, ReferenceRate.RateType.CDI)
        self.assertEqual(rate.periodicity, ReferenceRate.Periodicity.ANNUAL)
        self.assertEqual(rate.source, "manual")

    def test_get_latest_cdi_rate_returns_most_recent_rate(self):
        """Deve buscar o CDI mais recente por data."""

        old_rate = save_reference_rate(
            date=date(2026, 4, 1),
            value=Decimal("0.10000000"),
        )
        latest_rate = save_reference_rate(
            date=date(2026, 5, 1),
            value=Decimal("0.12000000"),
        )

        self.assertEqual(get_latest_cdi_rate(), latest_rate)
        self.assertNotEqual(get_latest_cdi_rate(), old_rate)

    def test_get_latest_cdi_rate_raises_clear_error_when_missing(self):
        """Deve retornar erro claro quando nao houver CDI cadastrado."""

        with self.assertRaisesMessage(
            ValidationError,
            "Nenhuma taxa de referencia cadastrada.",
        ):
            get_latest_cdi_rate()


class YieldSimulationServiceTests(TestCase):
    """Garante calculos de estimativa por percentual do CDI."""

    def setUp(self):
        """Cria conta base para estimativas por conta."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1000.00"),
        )

    def test_simulate_cdi_yield_at_100_percent(self):
        """Deve estimar rendimento de 100 por cento do CDI."""

        estimate = simulate_cdi_yield(
            amount=Decimal("1000.00"),
            months=12,
            annual_cdi_rate=Decimal("0.12000000"),
            cdi_percentage=Decimal("100.0000"),
        )

        self.assertEqual(estimate["final_amount"], Decimal("1120.00"))
        self.assertEqual(estimate["estimated_yield"], Decimal("120.00"))
        self.assertEqual(estimate["effective_annual_rate"], Decimal("0.12000000"))

    def test_simulate_cdi_yield_at_110_percent(self):
        """Deve estimar rendimento de 110 por cento do CDI."""

        estimate = simulate_cdi_yield(
            amount=Decimal("1000.00"),
            months=12,
            annual_cdi_rate=Decimal("0.10000000"),
            cdi_percentage=Decimal("110.0000"),
        )

        self.assertEqual(estimate["final_amount"], Decimal("1110.00"))
        self.assertEqual(estimate["estimated_yield"], Decimal("110.00"))
        self.assertEqual(estimate["effective_annual_rate"], Decimal("0.11000000"))

    def test_estimate_account_yield_uses_account_balance_by_default(self):
        """Deve usar saldo atual da conta quando amount nao for informado."""

        save_reference_rate(date=date(2026, 5, 1), value=Decimal("0.12000000"))
        AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        estimate = estimate_account_yield(account=self.account, months=12)

        self.assertEqual(estimate["initial_amount"], Decimal("1000.00"))
        self.assertEqual(estimate["final_amount"], Decimal("1120.00"))

    def test_estimate_account_yield_uses_custom_amount(self):
        """Deve usar valor informado quando amount for preenchido."""

        save_reference_rate(date=date(2026, 5, 1), value=Decimal("0.12000000"))
        AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        estimate = estimate_account_yield(
            account=self.account,
            months=12,
            amount=Decimal("2000.00"),
        )

        self.assertEqual(estimate["initial_amount"], Decimal("2000.00"))
        self.assertEqual(estimate["final_amount"], Decimal("2240.00"))

    def test_estimate_account_yield_without_active_config_raises_error(self):
        """Deve rejeitar conta sem configuracao ativa."""

        with self.assertRaisesMessage(
            ValidationError,
            "Conta nao possui configuracao de rendimento.",
        ):
            estimate_account_yield(account=self.account, months=12)

    def test_estimate_account_yield_with_none_type_returns_zero_yield(self):
        """Conta sem rendimento deve retornar estimativa zerada."""

        AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.NONE,
        )

        estimate = estimate_account_yield(account=self.account, months=12)

        self.assertEqual(estimate["initial_amount"], Decimal("1000.00"))
        self.assertEqual(estimate["final_amount"], Decimal("1000.00"))
        self.assertEqual(estimate["estimated_yield"], Decimal("0.00"))
        self.assertIsNone(estimate["rate"])
