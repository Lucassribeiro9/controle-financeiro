"""Tests das views do app recurrences."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from accounts.models import FinancialAccount
from institutions.models import Institution
from recurrences.models import Recurrence
from transactions.models import Transaction


class RecurrenceViewsTests(TestCase):
    """Garante fluxo de confirmar, ignorar e ajustar previsoes."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.recurrence = Recurrence.objects.create(
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
        )

    def test_monthly_forecasts_returns_month_items(self):
        response = self.client.get(
            reverse("recurrences:monthly-forecasts", kwargs={"year": 2026, "month": 6})
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["id"], self.forecast.id)

    def test_forecasts_page_lists_month_items(self):
        response = self.client.get(
            reverse("recurrences:forecasts-page", kwargs={"year": 2026, "month": 6})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recurrences/forecasts.html")
        self.assertContains(response, "Internet residencial")
        self.assertContains(response, "Confirmar")
        self.assertContains(response, 'class="badge badge-info"', html=False)

    def test_forecasts_filter_page_uses_query_period(self):
        response = self.client.get(
            reverse("recurrences:forecasts-filter-page"),
            data={"year": 2026, "month": 6},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], 2026)
        self.assertEqual(response.context["month"], 6)
        self.assertTemplateUsed(response, "recurrences/forecasts.html")
        self.assertContains(response, "Internet residencial")

    def test_forecasts_filter_page_uses_current_period_by_default(self):
        today = timezone.localdate()

        response = self.client.get(reverse("recurrences:forecasts-filter-page"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], today.year)
        self.assertEqual(response.context["month"], today.month)

    def test_confirm_forecast_sets_pending_and_expense(self):
        response = self.client.post(
            reverse("recurrences:confirm-forecast", kwargs={"transaction_id": self.forecast.id})
        )
        self.forecast.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(self.forecast.transaction_type, Transaction.TransactionType.EXPENSE)

    def test_ignore_forecast_sets_ignored_status(self):
        response = self.client.post(
            reverse("recurrences:ignore-forecast", kwargs={"transaction_id": self.forecast.id})
        )
        self.forecast.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.IGNORED)

    def test_adjust_forecast_updates_amount(self):
        response = self.client.post(
            reverse("recurrences:adjust-forecast", kwargs={"transaction_id": self.forecast.id}),
            data={"amount": "135.50"},
        )
        self.forecast.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.forecast.amount, Decimal("135.50"))
        self.assertIn("[REC_ADJUST]", self.forecast.notes)

    def test_adjust_forecast_requires_positive_amount(self):
        response = self.client.post(
            reverse("recurrences:adjust-forecast", kwargs={"transaction_id": self.forecast.id}),
            data={"amount": "0"},
        )

        self.assertEqual(response.status_code, 400)
