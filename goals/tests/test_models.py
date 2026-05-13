"""Tests dos models do app goals."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from institutions.models import Institution


class GoalModelTests(TestCase):
    """Garante as regras principais do model Goal."""

    def setUp(self):
        """Cria dados base para os cenarios de objetivos."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1500.00"),
        )
        self.category = Category.objects.create(name="Delivery")

    def test_create_accumulation_goal_with_account(self):
        """Deve criar objetivo de acumulo vinculado a uma conta."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("15000.00"),
            start_date=date(2026, 5, 1),
        )
        goal.accounts.add(self.account)

        self.assertEqual(goal.name, "Reserva de emergencia")
        self.assertEqual(goal.accounts.count(), 1)
        self.assertTrue(goal.is_active)

    def test_create_reduction_goal_with_category(self):
        """Deve criar objetivo de reducao vinculado a uma categoria."""

        goal = Goal(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        goal.full_clean()
        goal.save()

        self.assertEqual(goal.category, self.category)

    def test_target_amount_must_be_positive(self):
        """Nao deve validar objetivo com valor alvo zero ou negativo."""

        goal = Goal(
            name="Valor invalido",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("0.00"),
            start_date=date(2026, 5, 1),
        )

        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_reduction_goal_requires_category(self):
        """Objetivo de reducao deve exigir categoria vinculada."""

        goal = Goal(
            name="Reduzir gastos",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("600.00"),
            start_date=date(2026, 5, 1),
        )

        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_target_date_must_be_after_start_date(self):
        """Data alvo deve ser posterior a data de inicio."""

        goal = Goal(
            name="Viagem",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("5000.00"),
            start_date=date(2026, 5, 1),
            target_date=date(2026, 5, 1),
        )

        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_str_returns_name(self):
        """O __str__ deve retornar o nome do objetivo."""

        goal = Goal(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("15000.00"),
            start_date=date(2026, 5, 1),
        )

        self.assertEqual(str(goal), "Reserva de emergencia")


class MonthlyGoalModelTests(TestCase):
    """Garante as regras principais do model MonthlyGoal."""

    def setUp(self):
        """Cria objetivo base para os cenarios de meta mensal."""

        self.goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("15000.00"),
            start_date=date(2026, 5, 1),
        )

    def test_create_monthly_goal(self):
        """Deve criar meta mensal vinculada a um objetivo."""

        monthly_goal = MonthlyGoal.objects.create(
            goal=self.goal,
            year=2026,
            month=5,
            target_amount=Decimal("400.00"),
        )

        self.assertEqual(monthly_goal.goal, self.goal)
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.ON_TRACK)
        self.assertEqual(monthly_goal.current_amount, Decimal("0.00"))

    def test_month_must_be_between_one_and_twelve(self):
        """Nao deve validar meta mensal com mes fora do intervalo."""

        monthly_goal = MonthlyGoal(
            goal=self.goal,
            year=2026,
            month=13,
            target_amount=Decimal("400.00"),
        )

        with self.assertRaises(ValidationError):
            monthly_goal.full_clean()

    def test_target_amount_must_be_positive(self):
        """Nao deve validar meta mensal com valor alvo zero ou negativo."""

        monthly_goal = MonthlyGoal(
            goal=self.goal,
            year=2026,
            month=5,
            target_amount=Decimal("0.00"),
        )

        with self.assertRaises(ValidationError):
            monthly_goal.full_clean()

    def test_current_amount_cannot_be_negative(self):
        """Nao deve validar meta mensal com valor atual negativo."""

        monthly_goal = MonthlyGoal(
            goal=self.goal,
            year=2026,
            month=5,
            target_amount=Decimal("400.00"),
            current_amount=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            monthly_goal.full_clean()

    def test_disallows_duplicate_monthly_goal_for_same_goal_year_and_month(self):
        """Nao deve permitir duas metas mensais iguais para o mesmo objetivo."""

        MonthlyGoal.objects.create(
            goal=self.goal,
            year=2026,
            month=5,
            target_amount=Decimal("400.00"),
        )

        with self.assertRaises(IntegrityError):
            MonthlyGoal.objects.create(
                goal=self.goal,
                year=2026,
                month=5,
                target_amount=Decimal("500.00"),
            )

    def test_str_returns_goal_and_period(self):
        """O __str__ deve retornar objetivo e periodo da meta mensal."""

        monthly_goal = MonthlyGoal(
            goal=self.goal,
            year=2026,
            month=5,
            target_amount=Decimal("400.00"),
        )

        self.assertEqual(str(monthly_goal), "Reserva de emergencia - 2026-05")
