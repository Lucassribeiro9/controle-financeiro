"""Tests das views do app insights."""

from decimal import Decimal

from core.testing import AuthenticatedTestCase
from django.urls import reverse

from categories.models import Category
from goals.models import Goal, MonthlyGoal
from insights.models import IgnoredPattern, Insight


class InsightViewTests(AuthenticatedTestCase):
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
        self.assertContains(response, 'class="badge badge-warning"', html=False)

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
            reverse("insights:approve", kwargs={"insight_id": self.insight.id}),
            follow=True
        )

        self.insight.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("insights:page"))
        self.assertEqual(self.insight.status, Insight.Status.APPROVED)
        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(MonthlyGoal.objects.count(), 1)
        
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Insight aprovado com sucesso.")

    def test_approve_twice_does_not_duplicate_records(self):
        url = reverse("insights:approve", kwargs={"insight_id": self.insight.id})

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(MonthlyGoal.objects.count(), 1)

    def _existing_goal_with_other_amount(self):
        other = Insight.objects.create(
            title="Outro limite",
            message="Outra sugestao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal("300.00"),
            source_key="other",
        )
        self.client.post(reverse("insights:approve", kwargs={"insight_id": other.id}))

    def test_approve_with_existing_goal_shows_comparison_without_writing(self):
        self._existing_goal_with_other_amount()

        response = self.client.post(
            reverse("insights:approve", kwargs={"insight_id": self.insight.id})
        )

        self.insight.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "insights/confirm_approve.html")
        self.assertContains(response, "300,00")
        self.assertContains(response, "500,00")
        self.assertEqual(self.insight.status, Insight.Status.PENDING)
        self.assertEqual(MonthlyGoal.objects.get().target_amount, Decimal("300.00"))

    def test_approve_with_existing_goal_update_changes_amount(self):
        self._existing_goal_with_other_amount()

        response = self.client.post(
            reverse("insights:approve", kwargs={"insight_id": self.insight.id}),
            data={"existing_goal_action": "update"},
        )

        self.insight.refresh_from_db()
        self.assertRedirects(response, reverse("insights:page"))
        self.assertEqual(self.insight.status, Insight.Status.APPROVED)
        self.assertEqual(MonthlyGoal.objects.get().target_amount, Decimal("500.00"))
        self.assertEqual(Goal.objects.count(), 1)

    def test_approve_with_existing_goal_keep_preserves_amount(self):
        self._existing_goal_with_other_amount()

        self.client.post(
            reverse("insights:approve", kwargs={"insight_id": self.insight.id}),
            data={"existing_goal_action": "keep"},
        )

        self.insight.refresh_from_db()
        self.assertEqual(self.insight.status, Insight.Status.APPROVED)
        self.assertEqual(MonthlyGoal.objects.get().target_amount, Decimal("300.00"))

    def test_ignore_insight_marks_item_as_ignored(self):
        response = self.client.post(
            reverse("insights:ignore", kwargs={"insight_id": self.insight.id}),
            follow=True
        )

        self.insight.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("insights:page"))
        self.assertEqual(self.insight.status, Insight.Status.IGNORED)
        self.assertEqual(Goal.objects.count(), 0)

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Insight ignorado.")

    def test_silence_insight_marks_item_and_creates_ignored_pattern(self):
        response = self.client.post(
            reverse("insights:silence", kwargs={"insight_id": self.insight.id}),
            follow=True
        )

        self.insight.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("insights:page"))
        self.assertEqual(self.insight.status, Insight.Status.SILENCED)
        self.assertTrue(
            IgnoredPattern.objects.filter(
                pattern_key=f"category-limit:{self.category.id}"
            ).exists()
        )

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Insight silenciado.")

    def test_approve_insight_with_removed_category_shows_error_message(self):
        self.category.delete()

        response = self.client.post(
            reverse("insights:approve", kwargs={"insight_id": self.insight.id}),
            follow=True,
        )

        self.insight.refresh_from_db()
        self.assertRedirects(response, reverse("insights:page"))
        self.assertEqual(self.insight.status, Insight.Status.PENDING)
        self.assertEqual(Goal.objects.count(), 0)
        messages = [str(message) for message in response.context["messages"]]
        self.assertEqual(messages, ["A categoria deste insight não existe mais."])
