"""Tests dos models do app rates."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from rates.models import AccountYieldConfig, ReferenceRate


class ReferenceRateModelTests(TestCase):
    """Garante regras principais do model ReferenceRate."""

    def test_create_valid_annual_cdi_rate(self):
        """Deve criar CDI anual valido em formato decimal financeiro."""

        rate = ReferenceRate(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 5, 1),
            value=Decimal("0.10650000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )

        rate.full_clean()
        rate.save()

        self.assertEqual(rate.value, Decimal("0.10650000"))

    def test_rejects_zero_or_negative_rate_value(self):
        """Deve rejeitar taxa menor ou igual a zero."""

        for value in (Decimal("0"), Decimal("-0.01000000")):
            with self.subTest(value=value):
                rate = ReferenceRate(
                    rate_type=ReferenceRate.RateType.CDI,
                    date=date(2026, 5, 1),
                    value=value,
                    periodicity=ReferenceRate.Periodicity.ANNUAL,
                )

                with self.assertRaises(ValidationError):
                    rate.full_clean()

    def test_disallows_duplicate_rate_for_same_type_date_and_periodicity(self):
        """Nao deve permitir CDI duplicado para mesma data e periodicidade."""

        ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 5, 1),
            value=Decimal("0.10650000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )

        with self.assertRaises(IntegrityError):
            ReferenceRate.objects.create(
                rate_type=ReferenceRate.RateType.CDI,
                date=date(2026, 5, 1),
                value=Decimal("0.11000000"),
                periodicity=ReferenceRate.Periodicity.ANNUAL,
            )


class AccountYieldConfigModelTests(TestCase):
    """Garante regras principais do model AccountYieldConfig."""

    def setUp(self):
        """Cria conta base para configuracoes de rendimento."""

        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho",
            institution=institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1000.00"),
        )

    def test_create_cdi_percentage_config(self):
        """Deve criar configuracao de 100 por cento do CDI."""

        config = AccountYieldConfig(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        config.full_clean()
        config.save()

        self.assertEqual(config.cdi_percentage, Decimal("100.0000"))

    def test_rejects_cdi_percentage_config_without_percentage(self):
        """Deve exigir percentual quando o rendimento for por CDI."""

        config = AccountYieldConfig(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
        )

        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_rejects_zero_or_negative_cdi_percentage(self):
        """Deve rejeitar percentual do CDI menor ou igual a zero."""

        for percentage in (Decimal("0"), Decimal("-10.0000")):
            with self.subTest(percentage=percentage):
                config = AccountYieldConfig(
                    account=self.account,
                    yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
                    cdi_percentage=percentage,
                )

                with self.assertRaises(ValidationError):
                    config.full_clean()

    def test_allows_none_config_without_percentage(self):
        """Deve permitir conta sem rendimento e sem percentual CDI."""

        config = AccountYieldConfig(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.NONE,
        )

        config.full_clean()
        config.save()

        self.assertIsNone(config.cdi_percentage)
