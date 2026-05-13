"""Tests dos servicos do app goals."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from goals.services import (
    calculate_goal_progress,
    create_monthly_goal_from_goal,
    update_monthly_goal_status,
)
from institutions.models import Institution
from transactions.models import Transaction


class GoalServiceTests(TestCase):
    """Garante as regras de negocio para objetivos e metas mensais."""

    def setUp(self):
        """Cria dados base para cenarios de objetivos."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1500.00"),
        )
        self.extra_account = FinancialAccount.objects.create(
            name="Poupanca",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        self.spending_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Delivery")

    def test_calculate_accumulation_goal_progress_uses_linked_accounts_balance(self):
        """Deve calcular progresso de acumulo somando contas vinculadas."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("10000.00"),
            start_date=date(2026, 5, 1),
        )
        goal.accounts.add(self.account, self.extra_account)

        progress = calculate_goal_progress(goal=goal)

        self.assertEqual(progress["current_amount"], Decimal("2000.00"))
        self.assertEqual(progress["target_amount"], Decimal("10000.00"))
        self.assertEqual(progress["remaining_amount"], Decimal("8000.00"))
        self.assertEqual(progress["progress_percent"], Decimal("20.00"))

    def test_calculate_reduction_goal_progress_uses_category_expenses_for_month(self):
        """Deve calcular progresso de reducao com despesas da categoria no mes."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Pizza",
            amount=Decimal("80.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        Transaction.objects.create(
            description="Lanche",
            amount=Decimal("40.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 12),
        )

        progress = calculate_goal_progress(goal=goal, year=2026, month=5)

        self.assertEqual(progress["current_amount"], Decimal("120.00"))
        self.assertEqual(progress["remaining_amount"], Decimal("130.00"))
        self.assertEqual(progress["progress_percent"], Decimal("48.00"))

    def test_reduction_goal_progress_ignores_forecasted_ignored_and_canceled(self):
        """Nao deve somar despesas previstas, ignoradas ou canceladas."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        for status in (
            Transaction.PaymentStatus.FORECASTED,
            Transaction.PaymentStatus.IGNORED,
            Transaction.PaymentStatus.CANCELED,
        ):
            Transaction.objects.create(
                description=f"Delivery {status}",
                amount=Decimal("50.00"),
                transaction_type=Transaction.TransactionType.EXPENSE,
                status=status,
                account=self.spending_account,
                category=self.category,
                date=date(2026, 5, 10),
            )

        progress = calculate_goal_progress(goal=goal, year=2026, month=5)

        self.assertEqual(progress["current_amount"], Decimal("0.00"))

    def test_reduction_goal_requires_year_and_month_for_progress(self):
        """Objetivo de reducao deve exigir periodo para calcular progresso."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )

        with self.assertRaises(ValidationError):
            calculate_goal_progress(goal=goal)

    def test_create_monthly_goal_from_goal_uses_goal_target_when_omitted(self):
        """Deve criar meta mensal usando valor alvo do objetivo por padrao."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("10000.00"),
            start_date=date(2026, 5, 1),
        )

        monthly_goal = create_monthly_goal_from_goal(
            goal=goal,
            year=2026,
            month=5,
        )

        self.assertIsNotNone(monthly_goal.id)
        self.assertEqual(monthly_goal.target_amount, Decimal("10000.00"))

    def test_update_monthly_goal_status_marks_accumulation_as_achieved(self):
        """Deve marcar meta de acumulo como atingida ao alcancar o valor alvo."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 5, 1),
        )
        goal.accounts.add(self.account, self.extra_account)
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("2000.00"),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("2000.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.ACHIEVED)

    def test_update_monthly_goal_status_marks_reduction_as_at_risk(self):
        """Deve marcar reducao como em risco ao consumir 80 porcento do limite."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("250.00"),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("200.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.AT_RISK)

    def test_update_monthly_goal_status_marks_reduction_as_missed(self):
        """Deve marcar reducao como nao atingida ao passar do limite."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal("260.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("250.00"),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("260.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.MISSED)
