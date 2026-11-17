"""Testes dos templates de objetivos no visual novo (spec 017, item 3.7, #298)."""

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.testing import AuthenticatedTestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from institutions.models import Institution
from transactions.models import Transaction

ROOT = Path(__file__).resolve().parent.parent.parent
PAGE_CSS = "css/pages/goals.css"
LEGACY_MARKERS = (
    "data-table",
    'class="panel',
    "button-secondary",
    "goal-card",
    "period-form",
    "page-header",
    "metric-card",
    "detail-list",
    "table-responsive",
    'class="button',
)


class GoalTemplateTests(AuthenticatedTestCase):
    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1500.00"),
        )
        category = Category.objects.create(name="Delivery")
        self.accumulation = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 5, 1),
            target_date=date(2026, 12, 31),
        )
        self.accumulation.accounts.add(self.account)
        self.reduction = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 5, 1),
            category=category,
        )
        MonthlyGoal.objects.create(
            goal=self.reduction, year=2026, month=5, target_amount=Decimal("300.00")
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=category,
            date=date(2026, 5, 10),
        )
        self.query = {"year": 2026, "month": 5}

    def _get(self, name, *args):
        response = self.client.get(reverse(name, args=args), data=self.query)
        self.assertEqual(response.status_code, 200)
        return response

    def _assert_no_legacy(self, response):
        html = response.content.decode()
        for marker in LEGACY_MARKERS:
            self.assertNotIn(marker, html, marker)

    def test_list_uses_new_components(self):
        response = self._get("goals:list")

        self.assertContains(response, PAGE_CSS)
        self.assertContains(response, 'class="card gl-goal"', html=False)
        self.assertContains(response, 'class="progress')
        self.assertContains(response, "segmented gl-tabs")
        self.assertContains(response, 'aria-current="true"')
        self._assert_no_legacy(response)

    def test_list_marks_progress_over_when_goal_at_risk(self):
        response = self._get("goals:list")

        self.assertContains(response, "progress progress--over")

    def test_list_progress_width_uses_dot_decimal(self):
        response = self._get("goals:list")

        self.assertContains(response, "width: 75.00%")
        self.assertNotContains(response, "width: 75,00%")

    def test_list_has_period_in_topbar_and_content(self):
        response = self._get("goals:list")

        self.assertContains(response, 'name="month"', count=2)
        self.assertContains(response, 'name="year"', count=2)

    def test_list_empty_state_uses_component(self):
        Goal.objects.update(is_active=False)

        response = self._get("goals:list")

        self.assertContains(response, 'class="empty"')
        self.assertContains(response, "Nenhum objetivo ativo cadastrado.")
        self._assert_no_legacy(response)

    def test_monthly_goals_uses_list_table(self):
        response = self._get("goals:monthly-goals")

        self.assertContains(response, PAGE_CSS)
        self.assertContains(response, "list-table")
        self.assertContains(response, "list-table__amount")
        self.assertContains(response, "segmented gl-tabs")
        self._assert_no_legacy(response)

    def test_monthly_goals_empty_state_uses_component(self):
        MonthlyGoal.objects.all().delete()

        response = self._get("goals:monthly-goals")

        self.assertContains(response, 'class="empty"')
        self.assertContains(response, "Nenhuma meta mensal no período.")

    def test_detail_uses_new_components(self):
        response = self._get("goals:detail", self.reduction.id)

        self.assertContains(response, PAGE_CSS)
        self.assertContains(response, "summary-rows")
        self.assertContains(response, "progress")
        self.assertContains(response, "list-table")
        self.assertContains(response, "btn btn--secondary")
        self.assertContains(response, "gl-back")
        self.assertContains(response, "Reduzir delivery")
        self._assert_no_legacy(response)

    def test_detail_without_accounts_shows_empty_state(self):
        response = self._get("goals:detail", self.reduction.id)

        self.assertContains(response, "Nenhuma conta vinculada.")
        self.assertContains(response, 'class="empty"')

    def test_page_css_exists_without_literal_colors(self):
        css = (ROOT / "static" / "css" / "pages" / "goals.css").read_text()

        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", css))
        self.assertNotIn("rgb(", css)
