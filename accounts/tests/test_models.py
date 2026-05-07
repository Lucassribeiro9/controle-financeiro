"""Tests dos models do app accounts."""

from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution


class FinancialAccountModelTests(TestCase):
    """Garante as regras principais do model FinancialAccount."""

    def setUp(self):
        """Cria instituicoes base para os cenarios de teste."""

        self.inter = Institution.objects.create(name="Inter", code="077")
        self.nubank = Institution.objects.create(name="Nubank", code="260")

    def test_create_account_with_decimal_balance(self):
        """Deve criar conta com saldo em Decimal e moeda BRL padrao."""

        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1500.50"),
        )

        self.assertEqual(account.balance, Decimal("1500.50"))
        self.assertEqual(account.currency, FinancialAccount.Currency.BRL)

    def test_account_must_belong_to_an_institution(self):
        """Deve exigir instituicao para criar conta financeira."""

        with self.assertRaises(IntegrityError):
            FinancialAccount.objects.create(
                name="Conta sem instituicao",
                account_type=FinancialAccount.AccountType.CHECKING,
                balance=Decimal("100.00"),
            )

    def test_str_returns_account_and_institution_name(self):
        """O __str__ deve combinar nome da conta e nome da instituicao."""

        account = FinancialAccount.objects.create(
            name="Poupanca",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.SAVINGS,
        )

        self.assertEqual(str(account), "Poupanca (Inter)")

    def test_allows_same_account_name_in_different_institutions(self):
        """Deve permitir mesmo nome em instituicoes diferentes."""

        FinancialAccount.objects.create(
            name="Conta principal",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
        )
        account_in_other_institution = FinancialAccount.objects.create(
            name="Conta principal",
            institution=self.nubank,
            account_type=FinancialAccount.AccountType.CHECKING,
        )

        self.assertEqual(account_in_other_institution.name, "Conta principal")

    def test_disallows_duplicate_account_name_in_same_institution(self):
        """Nao deve permitir nome duplicado na mesma instituicao."""

        FinancialAccount.objects.create(
            name="Conta principal",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
        )

        with self.assertRaises(IntegrityError):
            FinancialAccount.objects.create(
                name="Conta principal",
                institution=self.inter,
                account_type=FinancialAccount.AccountType.SAVINGS,
            )
