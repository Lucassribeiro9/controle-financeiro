"""Tests das views do app goals."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from institutions.models import Institution
from transactions.models import Transaction


class GoalViewTests(TestCase):
    """Garante paginas de acompanhamento de objetivos e metas."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1500.00"),
        )
        self.category = Category.objects.create(name="Delivery")
        self.accumulation_goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 5, 1),
            target_date=date(2026, 12, 31),
        )
        self.accumulation_goal.accounts.add(self.account)
        self.reduction_goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        self.monthly_goal = MonthlyGoal.objects.create(
            goal=self.reduction_goal,
            year=2026,
            month=5,
            target_amount=Decimal("300.00"),
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 10),
        )

    def test_goal_list_page_returns_success(self):
        """Deve renderizar a pagina de objetivos."""

        response = self.client.get(
            reverse("goals:list"),
            data={"year": 2026, "month": 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "goals/list.html")
        self.assertContains(response, "Reserva de emergencia")
        self.assertContains(response, "Reduzir delivery")

    def test_goal_list_page_uses_current_period_by_default(self):
        """Deve usar o mes atual quando a query string nao informar periodo."""

        today = timezone.localdate()

        response = self.client.get(reverse("goals:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], today.year)
        self.assertEqual(response.context["month"], today.month)

    def test_goal_list_page_exposes_progress_in_context(self):
        """Deve exibir progresso calculado no contexto da tela."""

        response = self.client.get(
            reverse("goals:list"),
            data={"year": 2026, "month": 5},
        )

        first_summary = response.context["goal_summaries"][0]

        self.assertIn("progress", first_summary)
        self.assertContains(response, "75,00%")

    def test_monthly_goals_page_lists_period_items_and_updates_status(self):
        """Deve listar metas mensais do periodo com status atualizado."""

        response = self.client.get(
            reverse("goals:monthly-goals"),
            data={"year": 2026, "month": 5},
        )

        self.monthly_goal.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "goals/monthly_goals.html")
        self.assertContains(response, "Reduzir delivery")
        self.assertEqual(response.context["monthly_goals"], [self.monthly_goal])
        self.assertEqual(self.monthly_goal.current_amount, Decimal("250.00"))
        self.assertEqual(self.monthly_goal.status, MonthlyGoal.Status.AT_RISK)
        self.assertContains(response, 'class="badge badge-danger"', html=False)

    def test_goal_detail_page_returns_goal_monthly_goals_and_progress(self):
        """Deve renderizar detalhe do objetivo com metas e progresso."""

        response = self.client.get(
            reverse("goals:detail", kwargs={"goal_id": self.reduction_goal.id}),
            data={"year": 2026, "month": 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "goals/detail.html")
        self.assertContains(response, "Reduzir delivery")
        self.assertEqual(response.context["goal_summary"]["goal"], self.reduction_goal)
        self.assertEqual(
            response.context["goal_summary"]["progress"]["current_amount"],
            Decimal("250.00"),
        )
        self.assertEqual(
            response.context["goal_summary"]["monthly_goals"],
            [self.monthly_goal],
        )
