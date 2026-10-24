"""Tests dos services do app insights."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from insights.models import IgnoredPattern, Insight
from insights.tests.scenarios import build_realistic_month
from insights.services import (
    MonthlyGoalConflict,
    approve_insight,
    detect_recurrent_habits,
    generate_monthly_insights,
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

    def _limit_insight(self, amount="300.00", source_key=None):
        return Insight.objects.create(
            title="Limite sugerido",
            message="Criar meta para alimentacao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal(amount),
            source_key=source_key,
        )

    def test_approve_twice_does_not_duplicate_goal_or_monthly_goal(self):
        insight = self._limit_insight()

        approve_insight(insight=insight)
        approve_insight(insight=insight)

        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(MonthlyGoal.objects.count(), 1)

    def test_approve_reuses_goal_across_months_of_same_category(self):
        first = self._limit_insight(source_key="a")
        second = self._limit_insight(source_key="b")
        with patch("insights.services.timezone.localdate", return_value=date(2026, 5, 10)):
            approve_insight(insight=first)
        with patch("insights.services.timezone.localdate", return_value=date(2026, 6, 10)):
            approve_insight(insight=second)

        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(MonthlyGoal.objects.count(), 2)

    def test_approve_with_existing_monthly_goal_same_amount_links_it(self):
        first = approve_insight(insight=self._limit_insight(source_key="a"))
        second = approve_insight(insight=self._limit_insight(source_key="b"))

        self.assertEqual(second.monthly_goal_id, first.monthly_goal_id)
        self.assertEqual(MonthlyGoal.objects.count(), 1)

    def test_approve_with_different_amount_requires_decision(self):
        first = approve_insight(insight=self._limit_insight(source_key="a"))
        second = self._limit_insight(amount="450.00", source_key="b")

        with self.assertRaises(MonthlyGoalConflict) as ctx:
            approve_insight(insight=second)

        second.refresh_from_db()
        self.assertEqual(second.status, Insight.Status.PENDING)
        self.assertEqual(ctx.exception.monthly_goal.pk, first.monthly_goal_id)
        first.monthly_goal.refresh_from_db()
        self.assertEqual(first.monthly_goal.target_amount, Decimal("300.00"))

    def test_approve_keep_preserves_existing_amount(self):
        first = approve_insight(insight=self._limit_insight(source_key="a"))
        second = approve_insight(
            insight=self._limit_insight(amount="450.00", source_key="b"),
            existing_goal_action="keep",
        )

        self.assertEqual(second.status, Insight.Status.APPROVED)
        self.assertEqual(second.monthly_goal_id, first.monthly_goal_id)
        second.monthly_goal.refresh_from_db()
        self.assertEqual(second.monthly_goal.target_amount, Decimal("300.00"))

    def test_approve_update_changes_existing_amount(self):
        approve_insight(insight=self._limit_insight(source_key="a"))
        second = approve_insight(
            insight=self._limit_insight(amount="450.00", source_key="b"),
            existing_goal_action="update",
        )

        second.monthly_goal.refresh_from_db()
        self.assertEqual(second.monthly_goal.target_amount, Decimal("450.00"))
        self.assertEqual(MonthlyGoal.objects.count(), 1)
        self.assertEqual(Goal.objects.count(), 1)

    def test_approve_with_legacy_duplicate_goals_does_not_fail(self):
        for _ in range(2):
            Goal.objects.create(
                name="Limite: Alimentacao",
                goal_type=Goal.GoalType.REDUCTION,
                target_amount=Decimal("300.00"),
                start_date=date(2026, 1, 1),
                category=self.category,
            )

        approved = approve_insight(insight=self._limit_insight())

        self.assertEqual(Goal.objects.count(), 2)
        self.assertEqual(MonthlyGoal.objects.count(), 1)
        self.assertEqual(approved.monthly_goal.goal.pk, Goal.objects.order_by("pk").first().pk)

    def test_approve_rejects_unknown_existing_goal_action(self):
        with self.assertRaises(ValidationError):
            approve_insight(insight=self._limit_insight(), existing_goal_action="x")

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


class GenerateMonthlyInsightsTests(TestCase):
    """Valida a geracao mensal sobre um cenario realista."""

    def setUp(self):
        self.categories = build_realistic_month(year=2026, month=5)

    def _titles(self, insights):
        return sorted(insight.title for insight in insights)

    def test_creates_insights_only_for_qualifying_categories(self):
        created = generate_monthly_insights(year=2026, month=5)

        by_type = {}
        for insight in created:
            by_type.setdefault(insight.insight_type, set()).add(insight.category_id)
        mercado = self.categories["Mercado"].id
        transporte = self.categories["Transporte"].id
        self.assertEqual(
            by_type[Insight.InsightType.CATEGORY_LIMIT],
            {
                mercado,
                transporte,
                self.categories["Lazer"].id,
                self.categories["Saude"].id,
            },
        )
        self.assertEqual(by_type[Insight.InsightType.RECURRING_EXPENSE], {mercado})
        self.assertEqual(len(created), 5)

    def test_counts_pending_and_card_spending_but_not_excluded_or_uncategorized(self):
        created = generate_monthly_insights(year=2026, month=5)

        limits = {
            insight.category_id: insight.suggested_amount
            for insight in created
            if insight.insight_type == Insight.InsightType.CATEGORY_LIMIT
        }
        # Lazer: so o bar pendente; previsto e cancelado ficam fora.
        self.assertEqual(limits[self.categories["Lazer"].id], Decimal("90.00"))
        # Saude: compra pendente no cartao conta como gasto.
        self.assertEqual(limits[self.categories["Saude"].id], Decimal("120.00"))
        self.assertNotIn(None, {insight.category_id for insight in created})
        for insight in created:
            self.assertNotIn("None", insight.title)
            self.assertNotIn("None", insight.message)

    def test_does_not_leak_next_month_spending(self):
        generate_monthly_insights(year=2026, month=5)

        limit = Insight.objects.get(
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.categories["Mercado"],
        )
        self.assertEqual(limit.suggested_amount, Decimal("420.50"))

    def test_second_run_creates_nothing(self):
        generate_monthly_insights(year=2026, month=5)

        self.assertEqual(generate_monthly_insights(year=2026, month=5), [])
        self.assertEqual(Insight.objects.count(), 5)

    def test_silenced_limit_pattern_blocks_only_category_limit(self):
        mercado = self.categories["Mercado"]
        IgnoredPattern.objects.create(pattern_key=f"category-limit:{mercado.id}")

        created = generate_monthly_insights(year=2026, month=5)

        mercado_types = {i.insight_type for i in created if i.category_id == mercado.id}
        self.assertEqual(mercado_types, {Insight.InsightType.RECURRING_EXPENSE})

    def test_silenced_habit_pattern_blocks_only_recurring_expense(self):
        mercado = self.categories["Mercado"]
        IgnoredPattern.objects.create(pattern_key=f"habit-category:{mercado.id}")

        created = generate_monthly_insights(year=2026, month=5)

        self.assertNotIn(
            Insight.InsightType.RECURRING_EXPENSE, {i.insight_type for i in created}
        )
        self.assertEqual(len(created), 4)

    def test_empty_database_returns_empty_list(self):
        Transaction.objects.all().delete()

        self.assertEqual(generate_monthly_insights(year=2026, month=5), [])

    def test_recurring_average_is_quantized_to_cents(self):
        Transaction.objects.all().delete()
        account = FinancialAccount.objects.first()
        category = self.categories["Mercado"]
        for day, amount in ((1, "10.00"), (2, "10.00"), (3, "10.01")):
            Transaction.objects.create(
                description="Item",
                amount=Decimal(amount),
                transaction_type=Transaction.TransactionType.EXPENSE,
                status=Transaction.PaymentStatus.PAID,
                account=account,
                category=category,
                date=date(2026, 5, day),
            )

        created = detect_recurrent_habits(year=2026, month=5)

        self.assertEqual(created[0].suggested_amount, Decimal("10.00"))

    def test_messages_use_brl_and_month_name(self):
        generate_monthly_insights(year=2026, month=5)

        limit = Insight.objects.get(
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.categories["Mercado"],
        )
        self.assertIn("R$ 420,50", limit.message)
        self.assertIn("Maio/2026", limit.message)
        self.assertNotIn("neste mês", limit.message.lower())
        habit = Insight.objects.get(insight_type=Insight.InsightType.RECURRING_EXPENSE)
        self.assertIn("R$ 420,50", habit.message)
        self.assertIn("Maio/2026", habit.message)

    def test_approve_with_removed_category_raises_and_keeps_pending(self):
        generate_monthly_insights(year=2026, month=5)
        insight = Insight.objects.get(
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.categories["Transporte"],
        )
        self.categories["Transporte"].delete()
        insight.refresh_from_db()

        with self.assertRaises(ValidationError):
            approve_insight(insight=insight)

        insight.refresh_from_db()
        self.assertEqual(insight.status, Insight.Status.PENDING)
        self.assertFalse(Goal.objects.filter(name__startswith="Limite:").exists())
