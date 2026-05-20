"""Tests dos selectors do app accounts."""

from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from accounts.selectors import (
    get_account_summary,
    get_accounts_by_currency,
    get_active_accounts,
)
from institutions.models import Institution


class AccountSelectorTests(TestCase):
    """Garante consultas de contas financeiras."""

    def setUp(self):
        """Cria instituicoes base para os cenarios."""

        self.inter = Institution.objects.create(name="Inter", code="077")
        self.nomad = Institution.objects.create(name="Nomad", code="999")

    def test_get_active_accounts_returns_only_active_accounts(self):
        """Deve listar apenas contas ativas."""

        active_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
        )
        FinancialAccount.objects.create(
            name="Conta antiga",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.SAVINGS,
            is_active=False,
        )

        accounts = list(get_active_accounts())

        self.assertEqual(accounts, [active_account])

    def test_get_accounts_by_currency_filters_currency(self):
        """Deve filtrar contas pela moeda informada."""

        usd_account = FinancialAccount.objects.create(
            name="Global",
            institution=self.nomad,
            account_type=FinancialAccount.AccountType.GLOBAL,
            currency=FinancialAccount.Currency.USD,
            balance=Decimal("10.00"),
        )
        FinancialAccount.objects.create(
            name="Conta BRL",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            currency=FinancialAccount.Currency.BRL,
        )

        accounts = list(
            get_accounts_by_currency(currency=FinancialAccount.Currency.USD)
        )

        self.assertEqual(accounts, [usd_account])

    def test_get_account_summary_groups_accounts_by_currency(self):
        """Deve agrupar contas por moeda e somar saldos."""

        FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            currency=FinancialAccount.Currency.BRL,
            balance=Decimal("100.00"),
        )
        FinancialAccount.objects.create(
            name="Caixinha",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            currency=FinancialAccount.Currency.BRL,
            balance=Decimal("50.00"),
        )
        FinancialAccount.objects.create(
            name="Global",
            institution=self.nomad,
            account_type=FinancialAccount.AccountType.GLOBAL,
            currency=FinancialAccount.Currency.USD,
            balance=Decimal("20.00"),
            is_active=False,
        )

        summary = get_account_summary()

        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]["currency"], FinancialAccount.Currency.BRL)
        self.assertEqual(summary[0]["total_balance"], Decimal("150.00"))
        self.assertEqual(summary[0]["active_count"], 2)
        self.assertEqual(summary[1]["currency"], FinancialAccount.Currency.USD)
        self.assertEqual(summary[1]["total_balance"], Decimal("20.00"))
        self.assertEqual(summary[1]["inactive_count"], 1)
