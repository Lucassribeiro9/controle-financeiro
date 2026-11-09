"""Testes do selector de previsoes recorrentes (#218)."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from recurrences.models import Recurrence
from recurrences.selectors import get_recurring_forecasts_for_period
from transactions.models import Transaction


class GetRecurringForecastsForPeriodTests(TestCase):
    """Garante o criterio unico de previsao recorrente (decisao #218, opcao A)."""

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
        )

    def _create_forecast(self, *, description, when, status, recurrence):
        return Transaction.objects.create(
            description=description,
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=status,
            account=self.account,
            date=when,
            recurrence=recurrence,
        )

    def test_returns_empty_with_empty_database(self):
        result = get_recurring_forecasts_for_period(year=2026, month=6)

        self.assertEqual(list(result), [])

    def test_filters_by_type_period_and_link(self):
        linked = self._create_forecast(
            description="[REC] Internet residencial",
            when=date(2026, 6, 10),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=self.recurrence,
        )
        # Previsao orfa (recorrencia apagada ou legada): nao entra.
        self._create_forecast(
            description="[REC] Recorrencia removida",
            when=date(2026, 6, 10),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=None,
        )
        # Fora do periodo: nao entra.
        self._create_forecast(
            description="[REC] Internet residencial",
            when=date(2026, 7, 10),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=self.recurrence,
        )
        # Transacao normal (nao FORECAST) no mesmo mes: nao entra.
        Transaction.objects.create(
            description="Internet residencial",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.account,
            date=date(2026, 6, 10),
            recurrence=self.recurrence,
        )

        result = list(get_recurring_forecasts_for_period(year=2026, month=6))

        self.assertEqual(result, [linked])

    def test_statuses_filter_is_optional(self):
        forecasted = self._create_forecast(
            description="[REC] Internet residencial",
            when=date(2026, 6, 10),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=self.recurrence,
        )
        ignored = self._create_forecast(
            description="[REC] Internet residencial",
            when=date(2026, 6, 11),
            status=Transaction.PaymentStatus.IGNORED,
            recurrence=self.recurrence,
        )

        all_results = list(get_recurring_forecasts_for_period(year=2026, month=6))
        self.assertEqual(all_results, [forecasted, ignored])

        forecasted_only = list(
            get_recurring_forecasts_for_period(
                year=2026,
                month=6,
                statuses=[Transaction.PaymentStatus.FORECASTED],
            )
        )
        self.assertEqual(forecasted_only, [forecasted])

    def test_orders_by_date_then_description(self):
        second = self._create_forecast(
            description="[REC] Z",
            when=date(2026, 6, 10),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=self.recurrence,
        )
        first = self._create_forecast(
            description="[REC] A",
            when=date(2026, 6, 10),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=self.recurrence,
        )
        earliest = self._create_forecast(
            description="[REC] M",
            when=date(2026, 6, 5),
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence=self.recurrence,
        )

        result = list(get_recurring_forecasts_for_period(year=2026, month=6))

        self.assertEqual(result, [earliest, first, second])
