"""Tests do admin do app goals."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from goals.admin import GoalAdminForm
from goals.models import Goal
from institutions.models import Institution


class GoalAdminFormTests(TestCase):
    """Objetivo de acumulacao aceita contas de uma so moeda (ADR-016)."""

    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.brl = FinancialAccount.objects.create(
            name="Real",
            institution=institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("10.00"),
        )
        self.usd = FinancialAccount.objects.create(
            name="Dolar",
            institution=institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("10.00"),
            currency=FinancialAccount.Currency.USD,
        )

    def _data(self, accounts):
        return {
            "name": "Reserva",
            "goal_type": Goal.GoalType.ACCUMULATION,
            "target_amount": "1000.00",
            "start_date": date(2026, 1, 1),
            "is_active": True,
            "accounts": [account.pk for account in accounts],
        }

    def test_rejects_accounts_with_different_currencies(self):
        form = GoalAdminForm(data=self._data([self.brl, self.usd]))

        self.assertFalse(form.is_valid())
        self.assertIn("uma unica moeda", " ".join(form.errors["accounts"]))

    def test_accepts_accounts_with_single_currency(self):
        form = GoalAdminForm(data=self._data([self.brl]))

        self.assertTrue(form.is_valid(), form.errors)
