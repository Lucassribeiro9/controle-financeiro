"""Tests das views do app insights."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from goals.models import Goal, MonthlyGoal
from insights.models import IgnoredPattern, Insight


class InsightViewTests(TestCase):
    """Garante endpoints iniciais de revisao e decisao de insights."""

    def setUp(self):
        self.category = Category.objects.create(name="Alimentacao")
        self.insight = Insight.objects.create(
            title="Limite sugerido para Alimentacao",
            message="Criar meta para acompanhar alimentacao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal("500.00"),
            source_key=f"category-limit:{self.category.id}:2026-05",
        )

    def test_insight_list_returns_pending_items(self):
        Insight.objects.create(
            title="Insight ignorado",
            message="Ja ignorado.",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            status=Insight.Status.IGNORED,
            suggested_amount=Decimal("50.00"),
        )

        response = self.client.get(reverse("insights:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.insight.id)

    def test_insight_page_returns_pending_items(self):
        response = self.client.get(reverse("insights:page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "insights/list.html")
        self.assertContains(response, self.insight.title)
        self.assertContains(response, "Aprovar")

    def test_insight_list_can_filter_by_status(self):
        self.insight.status = Insight.Status.IGNORED
        self.insight.save(update_fields=["status", "updated_at"])

        response = self.client.get(
            reverse("insights:list"),
            data={"status": Insight.Status.IGNORED},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["status"], Insight.Status.IGNORED)

    def test_recent_insights_respects_limit(self):
        Insight.objects.create(
            title="Outro insight",
            message="Historico curto.",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            suggested_amount=Decimal("20.00"),
        )

        response = self.client.get(reverse("insights:recent"), data={"limit": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_recent_insights_rejects_invalid_limit(self):
        response = self.client.get(reverse("insights:recent"), data={"limit": "abc"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Campo limit inválido.")

    def test_approve_insight_creates_monthly_goal(self):
        response = self.client.post(
            reverse("insights:approve", kwargs={"insight_id": self.insight.id})
        )

        self.insight.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.insight.status, Insight.Status.APPROVED)
        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(MonthlyGoal.objects.count(), 1)
        self.assertEqual(response.json()["monthly_goal_id"], self.insight.monthly_goal_id)

    def test_ignore_insight_marks_item_as_ignored(self):
        response = self.client.post(
            reverse("insights:ignore", kwargs={"insight_id": self.insight.id})
        )

        self.insight.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.insight.status, Insight.Status.IGNORED)
        self.assertEqual(Goal.objects.count(), 0)

    def test_silence_insight_marks_item_and_creates_ignored_pattern(self):
        response = self.client.post(
            reverse("insights:silence", kwargs={"insight_id": self.insight.id})
        )

        self.insight.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.insight.status, Insight.Status.SILENCED)
        self.assertTrue(
            IgnoredPattern.objects.filter(
                pattern_key=f"category-limit:{self.category.id}"
            ).exists()
        )
