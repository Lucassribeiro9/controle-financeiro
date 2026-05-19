"""Tests dos seletores do app goals."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from goals.models import Goal, MonthlyGoal
from goals.selectors import (
    get_active_goals,
    get_goal_detail,
    get_monthly_goals_for_period,
)
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

    def test_get_monthly_goals_for_period_filters_period(self):
        """Deve listar metas mensais do periodo informado."""

        MonthlyGoal.objects.create(
            goal=self.goal,
            year=2026,
            month=6,
            target_amount=Decimal("400.00"),
        )

        monthly_goals = list(get_monthly_goals_for_period(year=2026, month=5))

        self.assertEqual(monthly_goals, [self.monthly_goal])

    def test_get_goal_detail_returns_goal_progress_and_monthly_goals(self):
        """Deve retornar detalhe do objetivo com progresso e metas do periodo."""

        summary = get_goal_detail(goal_id=self.goal.id, year=2026, month=5)

        self.assertEqual(summary["goal"], self.goal)
        self.assertEqual(summary["progress"]["current_amount"], Decimal("1500.00"))
        self.assertEqual(summary["monthly_goals"], [self.monthly_goal])
