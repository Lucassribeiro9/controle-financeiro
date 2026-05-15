"""Tests dos services do app insights."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from insights.models import IgnoredPattern, Insight
from insights.services import (
    approve_insight,
    detect_recurrent_habits,
    get_category_expense_total,
    ignore_insight,
    silence_insight,
    suggest_category_limit,
)
from institutions.models import Institution
from transactions.models import Transaction


class InsightServiceTests(TestCase):
    """Garante regras de sugestao, aprovacao e silencio de insights."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")

    def _expense(self, *, amount, day=10, status=Transaction.PaymentStatus.PAID):
        return Transaction.objects.create(
            description="Mercado",
            amount=Decimal(amount),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=status,
            account=self.account,
            category=self.category,
            date=date(2026, 5, day),
        )

    def test_get_category_expense_total_ignores_forecasted_items(self):
        self._expense(amount="100.00")
        self._expense(amount="50.00", status=Transaction.PaymentStatus.FORECASTED)

        total = get_category_expense_total(
            category=self.category,
            year=2026,
            month=5,
        )

        self.assertEqual(total, Decimal("100.00"))

    def test_suggest_category_limit_creates_pending_insight(self):
        self._expense(amount="120.00")

        insight = suggest_category_limit(category=self.category, year=2026, month=5)

        self.assertIsNotNone(insight)
        self.assertEqual(insight.status, Insight.Status.PENDING)
        self.assertEqual(insight.insight_type, Insight.InsightType.CATEGORY_LIMIT)
        self.assertEqual(insight.suggested_amount, Decimal("120.00"))
        self.assertEqual(insight.source_key, f"category-limit:{self.category.id}:2026-05")

    def test_suggest_category_limit_does_not_duplicate_monthly_source(self):
        self._expense(amount="120.00")

        suggest_category_limit(category=self.category, year=2026, month=5)
        duplicated = suggest_category_limit(category=self.category, year=2026, month=5)

        self.assertIsNone(duplicated)
        self.assertEqual(Insight.objects.count(), 1)

    def test_suggest_category_limit_respects_ignored_pattern(self):
        self._expense(amount="120.00")
        IgnoredPattern.objects.create(pattern_key=f"category-limit:{self.category.id}")

        insight = suggest_category_limit(category=self.category, year=2026, month=5)

        self.assertIsNone(insight)

    def test_approve_category_limit_creates_goal_and_monthly_goal(self):
        insight = Insight.objects.create(
            title="Limite sugerido",
            message="Criar meta para alimentacao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal("300.00"),
            source_key=f"category-limit:{self.category.id}:2026-05",
        )

        approved = approve_insight(insight=insight)

        self.assertEqual(approved.status, Insight.Status.APPROVED)
        self.assertIsNotNone(approved.monthly_goal)
        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(MonthlyGoal.objects.count(), 1)
        self.assertEqual(approved.monthly_goal.target_amount, Decimal("300.00"))

    def test_ignore_insight_marks_as_ignored_without_creating_goal(self):
        insight = Insight.objects.create(
            title="Habito recorrente",
            message="Sugestao de acompanhamento.",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            suggested_amount=Decimal("100.00"),
        )

        ignored = ignore_insight(insight=insight)

        self.assertEqual(ignored.status, Insight.Status.IGNORED)
        self.assertEqual(Goal.objects.count(), 0)

    def test_silence_insight_marks_as_silenced_and_saves_pattern(self):
        insight = Insight.objects.create(
            title="Limite sugerido",
            message="Criar meta para alimentacao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal("300.00"),
            source_key=f"category-limit:{self.category.id}:2026-05",
        )

        silenced = silence_insight(insight=insight)

        self.assertEqual(silenced.status, Insight.Status.SILENCED)
        self.assertTrue(
            IgnoredPattern.objects.filter(
                pattern_key=f"category-limit:{self.category.id}"
            ).exists()
        )

    def test_detect_recurrent_habits_creates_insight_for_repeated_category(self):
        self._expense(amount="10.00", day=1)
        self._expense(amount="20.00", day=2)
        self._expense(amount="30.00", day=3)

        created = detect_recurrent_habits(year=2026, month=5)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].insight_type, Insight.InsightType.RECURRING_EXPENSE)
        self.assertEqual(created[0].category, self.category)
        self.assertEqual(created[0].suggested_amount, Decimal("20.00"))
