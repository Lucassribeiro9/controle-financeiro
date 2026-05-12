"""Tests dos servicos do app recurrences."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from recurrences.models import Recurrence
from recurrences.services import (
    generate_monthly_recurrences_forecasts,
    has_relevant_amount_difference,
    match_recurrence_with_transaction,
    skip_recurrence_for_month,
)
from transactions.models import Transaction


class RecurrenceServiceTests(TestCase):
    """Garante as regras de negocio para recorrencias e previsoes."""

    def setUp(self):
        """Cria dados base para cenarios de recorrencia."""

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

    def test_generate_monthly_forecasts_creates_forecast_transaction(self):
        """Deve gerar previsao mensal para recorrencia ativa."""

        created_count = generate_monthly_recurrences_forecasts(year=2026, month=6)

        forecast = Transaction.objects.get(
            description="[REC] Internet residencial",
            date=date(2026, 6, 10),
        )

        self.assertEqual(created_count, 1)
        self.assertEqual(forecast.amount, Decimal("120.00"))
        self.assertEqual(forecast.account, self.account)

    def test_generated_forecast_is_created_with_forecasted_status(self):
        """Previsao deve nascer prevista e nao paga."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)

        forecast = Transaction.objects.get(
            description="[REC] Internet residencial",
            date=date(2026, 6, 10),
        )

        self.assertEqual(forecast.transaction_type, Transaction.TransactionType.FORECAST)
        self.assertEqual(forecast.status, Transaction.PaymentStatus.FORECASTED)
        self.assertNotEqual(forecast.status, Transaction.PaymentStatus.PAID)

    def test_skip_recurrence_for_month_marks_existing_forecast_as_ignored(self):
        """Ignorar recorrencia no mes deve marcar previsao como ignorada."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)

        updated_count = skip_recurrence_for_month(
            recurrence_id=self.recurrence.id,
            year=2026,
            month=6,
        )
        forecast = Transaction.objects.get(
            description="[REC] Internet residencial",
            date=date(2026, 6, 10),
        )

        self.assertEqual(updated_count, 1)
        self.assertEqual(forecast.status, Transaction.PaymentStatus.IGNORED)

    def test_match_recurrence_with_real_transaction_adds_match_note(self):
        """Reconciliar recorrencia deve anotar vinculacao na transacao real."""

        real_transaction = Transaction.objects.create(
            description="Internet residencial",
            amount=Decimal("118.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.account,
            date=date(2026, 6, 10),
        )

        matched = match_recurrence_with_transaction(
            recurrence_id=self.recurrence.id,
            transaction_id=real_transaction.id,
        )
        real_transaction.refresh_from_db()

        self.assertTrue(matched)
        self.assertIn(f"[REC_MATCH] recurrence_id={self.recurrence.id}", real_transaction.notes)

    def test_detect_relevant_amount_difference(self):
        """Deve detectar diferenca relevante entre valor previsto e real."""

        self.assertTrue(
            has_relevant_amount_difference(
                expected_amount=Decimal("120.00"),
                actual_amount=Decimal("135.00"),
            )
        )
        self.assertFalse(
            has_relevant_amount_difference(
                expected_amount=Decimal("120.00"),
                actual_amount=Decimal("120.00"),
            )
        )
