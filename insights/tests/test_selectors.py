"""Tests dos seletores do app insights."""

from decimal import Decimal

from django.test import TestCase

from categories.models import Category
from insights.models import IgnoredPattern, Insight
from insights.selectors import (
    get_ignored_patterns,
    get_insights_by_status,
    get_pending_insights,
    get_recent_insights,
)


class InsightSelectorTests(TestCase):
    """Garante consultas reutilizaveis para telas e dashboard."""

    def setUp(self):
        self.category = Category.objects.create(name="Alimentacao")
        self.pending = Insight.objects.create(
            title="Limite sugerido",
            message="Criar meta para alimentacao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal("800.00"),
            source_key="category-limit:1:2026-05",
        )
        self.ignored = Insight.objects.create(
            title="Sugestao ignorada",
            message="Sugestao ja ignorada.",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            status=Insight.Status.IGNORED,
            suggested_amount=Decimal("100.00"),
            source_key="habit-category:1:2026-05",
        )

    def test_get_pending_insights_returns_only_pending_items(self):
        insights = list(get_pending_insights())

        self.assertEqual(insights, [self.pending])

    def test_get_insights_by_status_filters_status(self):
        insights = list(get_insights_by_status(status=Insight.Status.IGNORED))

        self.assertEqual(insights, [self.ignored])

    def test_get_recent_insights_respects_limit(self):
        insights = list(get_recent_insights(limit=1))

        self.assertEqual(len(insights), 1)

    def test_get_ignored_patterns_lists_silenced_patterns(self):
        pattern = IgnoredPattern.objects.create(pattern_key="category-limit:1")

        self.assertEqual(list(get_ignored_patterns()), [pattern])
