"""Tests dos selectors do app rates."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from rates.models import AccountYieldConfig, ReferenceRate
from rates.selectors import (
    get_account_yield_summary,
    get_active_yield_configs,
    get_latest_rates,
    get_rate_history,
)


class RateSelectorTests(TestCase):
    """Garante consultas reutilizaveis de taxas e rendimentos."""

    def setUp(self):
        """Cria conta base para selectors."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1000.00"),
        )

    def test_get_latest_rates_returns_latest_cdi(self):
        """Deve retornar ultimo CDI disponivel por tipo."""

        ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 4, 1),
            value=Decimal("0.10000000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )
        latest_rate = ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 5, 1),
            value=Decimal("0.12000000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )

        latest_rates = get_latest_rates()

        self.assertEqual(latest_rates[ReferenceRate.RateType.CDI], latest_rate)

    def test_get_rate_history_lists_cdi_history(self):
        """Deve listar historico de CDI do mais recente para o antigo."""

        old_rate = ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 4, 1),
            value=Decimal("0.10000000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )
        latest_rate = ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 5, 1),
            value=Decimal("0.12000000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )

        history = list(get_rate_history(ReferenceRate.RateType.CDI))

        self.assertEqual(history, [latest_rate, old_rate])

    def test_get_active_yield_configs_lists_only_active_configs(self):
        """Deve listar apenas configuracoes ativas."""

        active_config = AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )
        inactive_account = FinancialAccount.objects.create(
            name="Reserva pausada",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("500.00"),
        )
        AccountYieldConfig.objects.create(
            account=inactive_account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("80.0000"),
            is_active=False,
        )

        configs = list(get_active_yield_configs())

        self.assertEqual(configs, [active_config])

    def test_get_account_yield_summary_returns_estimate(self):
        """Deve retornar estimativa para conta configurada."""

        ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 5, 1),
            value=Decimal("0.12000000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )
        config = AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        summary = get_account_yield_summary(months=12)

        self.assertEqual(summary[0]["config"], config)
        self.assertEqual(summary[0]["estimate"]["final_amount"], Decimal("1120.00"))
        self.assertEqual(summary[0]["error"], "")

    def test_get_account_yield_summary_returns_controlled_error_without_cdi(self):
        """Nao deve quebrar a tela inteira quando faltar CDI."""

        config = AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        summary = get_account_yield_summary(months=12)

        self.assertEqual(summary[0]["config"], config)
        self.assertIsNone(summary[0]["estimate"])
        self.assertIn("Nenhuma taxa de referencia cadastrada", summary[0]["error"])
