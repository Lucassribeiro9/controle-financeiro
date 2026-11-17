"""Testes dos templates de insights no visual novo (spec 017, item 3.7, #298)."""

from decimal import Decimal

from core.testing import AuthenticatedTestCase
from django.urls import reverse

from categories.models import Category
from goals.models import Goal, MonthlyGoal
from insights.models import Insight

LEGACY_MARKERS = (
    "insight-card",
    'class="panel',
    "button-secondary",
    "button-danger",
    "page-header",
    "action-row",
    'class="button',
)


class InsightTemplateTests(AuthenticatedTestCase):
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

    def _assert_no_legacy(self, response):
        html = response.content.decode()
        for marker in LEGACY_MARKERS:
            self.assertNotIn(marker, html, marker)

    def test_list_uses_cards_and_buttons(self):
        response = self.client.get(reverse("insights:page"))

        self.assertContains(response, 'class="card ins-item"', html=False)
        self.assertContains(response, "btn btn--primary")
        self.assertContains(response, "btn btn--secondary")
        self.assertContains(response, "btn btn--tertiary")
        self.assertContains(response, "R$ 500,00")
        self._assert_no_legacy(response)

    def test_list_keeps_post_forms(self):
        response = self.client.get(reverse("insights:page"))

        for name in ("approve", "ignore", "silence"):
            url = reverse(f"insights:{name}", args=[self.insight.id])
            self.assertContains(response, f'method="post" action="{url}"')

    def test_list_empty_state_uses_component(self):
        Insight.objects.all().delete()

        response = self.client.get(reverse("insights:page"))

        self.assertContains(response, 'class="empty"')
        self.assertContains(response, "Nenhum insight pendente no momento.")
        self._assert_no_legacy(response)

    def test_confirm_approve_uses_new_components(self):
        goal = Goal.objects.create(
            name="Meta Alimentacao",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("300.00"),
            start_date=self.insight.created_at.date(),
            category=self.category,
        )
        today = self.insight.created_at
        MonthlyGoal.objects.create(
            goal=goal, year=today.year, month=today.month,
            target_amount=Decimal("300.00"),
        )
        response = self.client.post(reverse("insights:approve", args=[self.insight.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "insights/confirm_approve.html")
        self.assertContains(response, "summary-rows")
        self.assertContains(response, "btn btn--primary")
        self.assertContains(response, "btn btn--secondary")
        self.assertContains(response, "R$ 300,00")
        self.assertContains(response, "R$ 500,00")
        self._assert_no_legacy(response)
