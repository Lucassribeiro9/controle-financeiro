"""Tests dos seletores do app goals."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from goals.selectors import (
    get_active_goals,
    get_goal_detail,
    get_monthly_goals_with_status,
)
from transactions.models import Transaction
from institutions.models import Institution


class GoalSelectorTests(TestCase):
    """Garante consultas reutilizaveis para as telas de objetivos."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1500.00"),
        )
        self.goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 5, 1),
        )
        self.goal.accounts.add(self.account)
        self.monthly_goal = MonthlyGoal.objects.create(
            goal=self.goal,
            year=2026,
            month=5,
            target_amount=Decimal("400.00"),
        )
        self.inactive_goal = Goal.objects.create(
            name="Objetivo pausado",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("1000.00"),
            start_date=date(2026, 5, 1),
            is_active=False,
        )

    def test_get_active_goals_returns_progress_for_active_items(self):
        """Deve listar apenas objetivos ativos com progresso calculado."""

        summaries = get_active_goals(year=2026, month=5)

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["goal"], self.goal)
        self.assertEqual(summaries[0]["progress"]["current_amount"], Decimal("1500.00"))
        self.assertEqual(summaries[0]["progress"]["progress_percent"], Decimal("75.00"))

    def test_get_monthly_goals_with_status_filters_period(self):
        """Deve listar metas mensais do periodo informado."""

        MonthlyGoal.objects.create(
            goal=self.goal,
            year=2026,
            month=6,
            target_amount=Decimal("400.00"),
        )

        monthly_goals = list(get_monthly_goals_with_status(year=2026, month=5))

        self.assertEqual(monthly_goals, [self.monthly_goal])

    def test_get_goal_detail_returns_goal_progress_and_monthly_goals(self):
        """Deve retornar detalhe do objetivo com progresso e metas do periodo."""

        summary = get_goal_detail(goal_id=self.goal.id, year=2026, month=5)

        self.assertEqual(summary["goal"], self.goal)
        self.assertEqual(summary["progress"]["current_amount"], Decimal("1500.00"))
        self.assertEqual(summary["monthly_goals"], [self.monthly_goal])


TODAY = date(2026, 6, 15)


class MonthlyGoalReadTimeStatusTests(TestCase):
    """Status calculado na leitura, sem gravar (ADR-016)."""

    def setUp(self):
        patcher = mock.patch(
            "goals.services.timezone.localdate", return_value=TODAY
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.category = Category.objects.create(name="Delivery")
        self.reduction = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            category=self.category,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 1, 1),
        )

    def _account(self, *, balance, currency=FinancialAccount.Currency.BRL, name="Conta"):
        return FinancialAccount.objects.create(
            name=name,
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal(balance),
            currency=currency,
        )

    def _expense(self, *, amount, day):
        return Transaction.objects.create(
            description="Pizza",
            amount=Decimal(amount),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            category=self.category,
            date=day,
        )

    def test_reduction_of_closed_month_is_calculated_by_competence(self):
        monthly_goal = MonthlyGoal.objects.create(
            goal=self.reduction, year=2026, month=3, target_amount=Decimal("300.00")
        )
        self._expense(amount="100.00", day=date(2026, 3, 10))
        # Lancado depois do fim do mes, mas com data dentro dele.
        self._expense(amount="250.00", day=date(2026, 3, 31))
        self._expense(amount="900.00", day=date(2026, 4, 1))

        goals = get_monthly_goals_with_status(year=2026, month=3)

        self.assertEqual([g.pk for g in goals], [monthly_goal.pk])
        self.assertEqual(goals[0].current_amount, Decimal("350.00"))
        self.assertEqual(goals[0].status, MonthlyGoal.Status.MISSED)
        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.current_amount, Decimal("0.00"))
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.ON_TRACK)

    def test_accumulation_of_closed_month_keeps_stored_snapshot(self):
        account = self._account(balance="2500.00")
        goal = Goal.objects.create(
            name="Reserva",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 1, 1),
        )
        goal.accounts.add(account)
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=3,
            target_amount=Decimal("2000.00"),
            current_amount=Decimal("2500.00"),
            status=MonthlyGoal.Status.ACHIEVED,
        )
        account.balance = Decimal("100.00")
        account.save(update_fields=["balance"])

        goals = get_monthly_goals_with_status(year=2026, month=3)

        self.assertEqual(goals[0].current_amount, Decimal("2500.00"))
        self.assertEqual(goals[0].status, MonthlyGoal.Status.ACHIEVED)

    def test_accumulation_of_current_month_uses_current_balance(self):
        account = self._account(balance="2500.00")
        goal = Goal.objects.create(
            name="Reserva",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 1, 1),
        )
        goal.accounts.add(account)
        MonthlyGoal.objects.create(
            goal=goal, year=2026, month=6, target_amount=Decimal("2000.00")
        )

        goals = get_monthly_goals_with_status(year=2026, month=6)

        self.assertEqual(goals[0].current_amount, Decimal("2500.00"))
        self.assertEqual(goals[0].status, MonthlyGoal.Status.ACHIEVED)

    def test_legacy_goal_with_mixed_currencies_returns_stored_values(self):
        brl = self._account(balance="1000.00", name="Real")
        usd = self._account(
            balance="500.00", currency=FinancialAccount.Currency.USD, name="Dolar"
        )
        goal = Goal.objects.create(
            name="Misto",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("1000.00"),
            start_date=date(2026, 1, 1),
        )
        goal.accounts.add(brl, usd)
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=6,
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("10.00"),
        )

        goals = get_monthly_goals_with_status(year=2026, month=6)

        self.assertEqual(goals[0].current_amount, Decimal("10.00"))
        self.assertEqual(goals[0].status, MonthlyGoal.Status.ON_TRACK)

    def test_goal_detail_shows_calculated_status(self):
        monthly_goal = MonthlyGoal.objects.create(
            goal=self.reduction, year=2026, month=6, target_amount=Decimal("300.00")
        )
        self._expense(amount="320.00", day=date(2026, 6, 2))

        detail = get_goal_detail(goal_id=self.reduction.pk, year=2026, month=6)

        shown = detail["monthly_goals"]
        self.assertEqual([g.pk for g in shown], [monthly_goal.pk])
        self.assertEqual(shown[0].status, MonthlyGoal.Status.MISSED)
        self.assertEqual(shown[0].current_amount, Decimal("320.00"))
        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.ON_TRACK)

    def test_goal_detail_does_not_break_with_mixed_currencies(self):
        brl = self._account(balance="1000.00", name="Real")
        usd = self._account(
            balance="500.00", currency=FinancialAccount.Currency.USD, name="Dolar"
        )
        goal = Goal.objects.create(
            name="Misto",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("1000.00"),
            start_date=date(2026, 1, 1),
        )
        goal.accounts.add(brl, usd)

        detail = get_goal_detail(goal_id=goal.pk, year=2026, month=6)

        self.assertEqual(detail["progress"]["current_amount"], Decimal("0.00"))

    def test_orders_by_calculated_status_then_name(self):
        other_category = Category.objects.create(name="Lazer")
        other = Goal.objects.create(
            name="Aaa lazer",
            goal_type=Goal.GoalType.REDUCTION,
            category=other_category,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 1, 1),
        )
        # Gravado: ambas on_track. Calculado: "Reduzir delivery" missed,
        # "Aaa lazer" on_track.
        MonthlyGoal.objects.create(
            goal=self.reduction, year=2026, month=6, target_amount=Decimal("300.00")
        )
        MonthlyGoal.objects.create(
            goal=other, year=2026, month=6, target_amount=Decimal("300.00")
        )
        self._expense(amount="400.00", day=date(2026, 6, 3))

        goals = get_monthly_goals_with_status(year=2026, month=6)

        self.assertEqual(
            [g.goal.name for g in goals], ["Reduzir delivery", "Aaa lazer"]
        )
