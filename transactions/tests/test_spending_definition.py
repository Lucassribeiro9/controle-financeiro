"""Garante que todos os modulos usam a mesma definicao de gasto (#211)."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from categories.selectors import get_categories_with_monthly_spent
from core.selectors import get_operational_home_context
from goals.models import Goal
from goals.services import calculate_goal_progress
from institutions.models import Institution
from insights.services import get_category_expense_total
from reports.selectors import get_category_expense_breakdown, get_monthly_expense_total
from transactions.constants import (
    EXCLUDED_SPENDING_STATUSES,
    SPENDING_TRANSACTION_TYPES,
)
from transactions.models import Transaction

EXPENSE = Transaction.TransactionType.EXPENSE
CARD_PURCHASE = Transaction.TransactionType.CARD_PURCHASE
BENEFIT_PURCHASE = Transaction.TransactionType.BENEFIT_PURCHASE
STATEMENT_PAYMENT = Transaction.TransactionType.STATEMENT_PAYMENT
Status = Transaction.PaymentStatus


class SpendingConstantsTests(TestCase):
    """Valida o conteudo da fonte unica de gasto."""

    def test_spending_types_exclude_statement_payment(self):
        self.assertCountEqual(
            SPENDING_TRANSACTION_TYPES, [EXPENSE, CARD_PURCHASE, BENEFIT_PURCHASE]
        )
        self.assertNotIn(STATEMENT_PAYMENT, SPENDING_TRANSACTION_TYPES)

    def test_excluded_statuses_are_canceled_ignored_and_forecasted(self):
        self.assertCountEqual(
            EXCLUDED_SPENDING_STATUSES,
            [Status.CANCELED, Status.IGNORED, Status.FORECASTED],
        )


class SpendingConsistencyTests(TestCase):
    """Os modulos precisam concordar sobre o gasto do mesmo mes."""

    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("5000.00"),
        )
        self.credit_card = Card.objects.create(
            name="Cartao Inter",
            institution=institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("3000.00"),
            statement_closing_day=10,
            statement_due_day=17,
            payment_account=self.account,
        )
        self.benefit_card = Card.objects.create(
            name="Vale",
            institution=institution,
            card_type=Card.CardType.BENEFIT,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Mercado")
        self.reference_date = date(2026, 5, 1)

    def _add(self, amount, transaction_type, status, *, card=None, day=10):
        return Transaction.objects.create(
            description=f"{transaction_type} {status}",
            amount=Decimal(amount),
            transaction_type=transaction_type,
            status=status,
            account=None if card else self.account,
            card=card,
            category=self.category,
            date=date(2026, 5, day),
        )

    def _populate(self):
        self._add("100.00", EXPENSE, Status.PAID)
        self._add("50.00", EXPENSE, Status.PENDING)
        self._add("200.00", CARD_PURCHASE, Status.PENDING, card=self.credit_card)
        self._add("30.00", BENEFIT_PURCHASE, Status.PENDING, card=self.benefit_card)
        for status in EXCLUDED_SPENDING_STATUSES:
            self._add("999.00", EXPENSE, status)
        self._add("380.00", STATEMENT_PAYMENT, Status.PAID, card=self.credit_card)

    def test_all_modules_report_the_same_category_spending(self):
        self._populate()
        goal = Goal.objects.create(
            name="Reduzir mercado",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        expected = Decimal("380.00")

        insights_total = get_category_expense_total(
            category=self.category, year=2026, month=5
        )
        goal_total = calculate_goal_progress(goal=goal, year=2026, month=5)[
            "current_amount"
        ]
        categories_total = next(
            c
            for c in get_categories_with_monthly_spent(self.reference_date)
            if c.pk == self.category.pk
        ).monthly_spent
        report_rows = get_category_expense_breakdown(year=2026, month=5)
        report_total = next(
            row["total_amount"]
            for row in report_rows
            if row["category_id"] == self.category.pk
        )

        self.assertEqual(insights_total, expected)
        self.assertEqual(goal_total, expected)
        self.assertEqual(categories_total, expected)
        self.assertEqual(report_total, expected)
        self.assertEqual(get_monthly_expense_total(year=2026, month=5), expected)

    def test_home_effective_spending_matches_other_modules(self):
        self._populate()

        summary = get_operational_home_context(today=date(2026, 5, 20))["summary"]

        home_total = (
            summary["realized"]["expenses"] + summary["pending"]["expenses"]
        )
        self.assertEqual(home_total, Decimal("380.00"))

    def test_statement_payment_is_never_spending(self):
        self._add("380.00", STATEMENT_PAYMENT, Status.PAID, card=self.credit_card)

        self.assertEqual(
            get_category_expense_total(category=self.category, year=2026, month=5),
            Decimal("0.00"),
        )
        self.assertEqual(
            get_monthly_expense_total(year=2026, month=5), Decimal("0.00")
        )
        category = next(
            c
            for c in get_categories_with_monthly_spent(self.reference_date)
            if c.pk == self.category.pk
        )
        self.assertEqual(category.monthly_spent, Decimal("0.00"))
