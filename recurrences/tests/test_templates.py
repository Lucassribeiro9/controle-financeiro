"""Testes do template de previsoes no visual novo (spec 017, item 3.7, #298)."""

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.testing import AuthenticatedTestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from institutions.models import Institution
from recurrences.models import Recurrence
from transactions.models import Transaction

ROOT = Path(__file__).resolve().parent.parent.parent
PAGE_CSS = "css/pages/recurrences.css"
LEGACY_MARKERS = (
    "data-table",
    'class="panel',
    "button-secondary",
    "forecast-card",
    "period-form",
    "page-header",
    "inline-form",
    "detail-list",
    'class="button',
)


class ForecastTemplateTests(AuthenticatedTestCase):
    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        recurrence = Recurrence.objects.create(
            name="Internet residencial",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
            requires_confirmation=True,
            is_active=True,
        )
        self.forecast = Transaction.objects.create(
            description="[REC] Internet residencial",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 6, 10),
            recurrence=recurrence,
        )

    def _get(self):
        response = self.client.get(
            reverse("recurrences:forecasts-page", kwargs={"year": 2026, "month": 6})
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_forecasts_use_list_table_and_buttons(self):
        response = self._get()

        self.assertContains(response, PAGE_CSS)
        self.assertContains(response, "list-table")
        self.assertContains(response, "list-table__amount")
        self.assertContains(response, "btn btn--primary")
        self.assertContains(response, "btn btn--secondary")
        self.assertContains(response, "R$ 120,00")
        html = response.content.decode()
        for marker in LEGACY_MARKERS:
            self.assertNotIn(marker, html, marker)

    def test_forecasts_keep_post_forms(self):
        response = self._get()

        for name in ("confirm-forecast", "ignore-forecast", "adjust-forecast"):
            url = reverse(f"recurrences:{name}", args=[self.forecast.id])
            self.assertContains(response, f'method="post" action="{url}"')
        self.assertContains(response, 'name="amount"')

    def test_forecasts_have_period_in_topbar_and_content(self):
        response = self._get()

        self.assertContains(response, 'name="month"', count=2)
        self.assertContains(response, 'name="year"', count=2)

    def test_forecasts_empty_state_uses_component(self):
        Transaction.objects.all().delete()

        response = self._get()

        self.assertContains(response, 'class="empty"')
        self.assertContains(response, "Nenhuma previsão recorrente no período.")

    def test_page_css_exists_without_literal_colors(self):
        css = (ROOT / "static" / "css" / "pages" / "recurrences.css").read_text()

        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", css))
        self.assertNotIn("rgb(", css)
