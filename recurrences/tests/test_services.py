"""Tests dos servicos do app recurrences."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from recurrences.models import Recurrence
from cards.models import Card, CardStatement
from recurrences.services import (
    confirm_forecast,
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

    def _create_homonym(self, *, recurrence_type=Recurrence.RecurrenceType.INCOME):
        """Cria segunda recorrencia com o mesmo nome, data, conta e cartao."""

        return Recurrence.objects.create(
            name=self.recurrence.name,
            expected_day=self.recurrence.expected_day,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=recurrence_type,
            expected_amount=self.recurrence.expected_amount,
            account=self.account,
            is_active=True,
        )

    def test_generated_forecast_is_linked_to_recurrence(self):
        """Previsao gerada deve guardar a recorrencia de origem."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)

        forecast = Transaction.objects.get(date=date(2026, 6, 10))

        self.assertEqual(forecast.recurrence, self.recurrence)

    def test_generate_with_homonym_recurrences_links_each_forecast(self):
        """Recorrencias homonimas geram uma previsao cada, com vinculo proprio."""

        other = self._create_homonym()

        created_count = generate_monthly_recurrences_forecasts(year=2026, month=6)

        self.assertEqual(created_count, 2)
        self.assertEqual(
            set(Transaction.objects.values_list("recurrence_id", flat=True)),
            {self.recurrence.id, other.id},
        )

    def test_generate_twice_with_homonyms_does_not_duplicate(self):
        """Gerar de novo nao duplica previsoes de recorrencias homonimas."""

        self._create_homonym()
        generate_monthly_recurrences_forecasts(year=2026, month=6)

        created_count = generate_monthly_recurrences_forecasts(year=2026, month=6)

        self.assertEqual(created_count, 0)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_skip_recurrence_for_month_affects_only_chosen_recurrence(self):
        """Pular o mes nao deve ignorar a previsao de recorrencia homonima."""

        other = self._create_homonym()
        generate_monthly_recurrences_forecasts(year=2026, month=6)

        updated_count = skip_recurrence_for_month(
            recurrence_id=other.id, year=2026, month=6
        )

        self.assertEqual(updated_count, 1)
        self.assertEqual(
            Transaction.objects.get(recurrence=other).status,
            Transaction.PaymentStatus.IGNORED,
        )
        self.assertEqual(
            Transaction.objects.get(recurrence=self.recurrence).status,
            Transaction.PaymentStatus.FORECASTED,
        )

    def test_skip_recurrence_for_month_works_after_rename(self):
        """Renomear a recorrencia nao impede pular a previsao ja gerada."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)
        self.recurrence.name = "Internet fibra"
        self.recurrence.save()

        updated_count = skip_recurrence_for_month(
            recurrence_id=self.recurrence.id, year=2026, month=6
        )

        self.assertEqual(updated_count, 1)

    def _assert_single_forecast_after(self, change) -> None:
        """Aplica a alteracao entre duas geracoes e garante uma unica transacao."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)
        change(Transaction.objects.get(recurrence=self.recurrence))

        created_count = generate_monthly_recurrences_forecasts(year=2026, month=6)

        self.assertEqual(created_count, 0)
        self.assertEqual(Transaction.objects.filter(recurrence=self.recurrence).count(), 1)

    def test_regenerate_after_adjusting_amount_does_not_duplicate(self):
        """Ajustar o valor da previsao nao permite recria-la."""

        def change(forecast):
            forecast.amount = Decimal("150.00")
            forecast.save()

        self._assert_single_forecast_after(change)

    def test_regenerate_after_ignoring_does_not_duplicate(self):
        """Previsao ignorada nao volta na proxima geracao."""

        def change(forecast):
            forecast.status = Transaction.PaymentStatus.IGNORED
            forecast.save()

        self._assert_single_forecast_after(change)

    def test_regenerate_after_skipping_month_does_not_duplicate(self):
        """Mes pulado nao e recriado na proxima geracao."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)
        skip_recurrence_for_month(recurrence_id=self.recurrence.id, year=2026, month=6)

        created_count = generate_monthly_recurrences_forecasts(year=2026, month=6)

        self.assertEqual(created_count, 0)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_regenerate_after_confirming_does_not_duplicate(self):
        """Previsao confirmada nao e recriada na proxima geracao."""

        def change(forecast):
            forecast.transaction_type = Transaction.TransactionType.EXPENSE
            forecast.status = Transaction.PaymentStatus.PENDING
            forecast.save()

        self._assert_single_forecast_after(change)

    def test_regenerate_after_changing_recurrence_fields_does_not_duplicate(self):
        """Mudar valor, dia, conta ou cartao da recorrencia nao duplica o mes."""

        other_account = FinancialAccount.objects.create(
            name="Conta reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("0.00"),
        )

        def change(_forecast):
            self.recurrence.expected_amount = Decimal("200.00")
            self.recurrence.expected_day = 20
            self.recurrence.account = other_account
            self.recurrence.save()

        self._assert_single_forecast_after(change)

    def test_regenerate_after_changing_forecast_date_in_same_month_does_not_duplicate(
        self,
    ):
        """Editar a data da transacao dentro do mes nao permite nova previsao."""

        def change(forecast):
            forecast.date = date(2026, 6, 25)
            forecast.save()

        self._assert_single_forecast_after(change)

    def test_generate_for_next_month_creates_new_forecast(self):
        """Deduplicacao e mensal: o mes seguinte gera nova previsao."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)

        created_count = generate_monthly_recurrences_forecasts(year=2026, month=7)

        self.assertEqual(created_count, 1)
        self.assertEqual(Transaction.objects.filter(recurrence=self.recurrence).count(), 2)

    def test_skip_recurrence_for_month_works_after_changing_expected_day(self):
        """Pular o mes ignora a previsao mesmo apos mudar o dia esperado."""

        generate_monthly_recurrences_forecasts(year=2026, month=6)
        self.recurrence.expected_day = 20
        self.recurrence.save()

        updated_count = skip_recurrence_for_month(
            recurrence_id=self.recurrence.id, year=2026, month=6
        )

        self.assertEqual(updated_count, 1)
        self.assertEqual(
            Transaction.objects.get(recurrence=self.recurrence).status,
            Transaction.PaymentStatus.IGNORED,
        )

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


class ConfirmForecastServiceTests(TestCase):
    """Garante o tipo, a fatura e o rollback na confirmacao de previsoes."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.credit_card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )
        self.benefit_card = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("100.00"),
            balance=Decimal("100.00"),
        )

    def _forecast(self, *, recurrence_type, card=None, account=None, day=10):
        recurrence = Recurrence.objects.create(
            name="Streaming",
            expected_day=day,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=recurrence_type,
            expected_amount=Decimal("50.00"),
            account=account,
            card=card,
        )
        generate_monthly_recurrences_forecasts(year=2026, month=6)
        return Transaction.objects.get(recurrence=recurrence)

    def test_subscription_on_credit_card_becomes_card_purchase_in_statement(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            card=self.credit_card,
        )

        confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertEqual(
            forecast.transaction_type, Transaction.TransactionType.CARD_PURCHASE
        )
        self.assertEqual(forecast.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(forecast.card, self.credit_card)
        self.assertIsNone(forecast.account)
        self.assertEqual(forecast.statement.card, self.credit_card)
        self.assertEqual((forecast.statement.year, forecast.statement.month), (2026, 6))
        self.assertEqual(forecast.statement.expected_amount, Decimal("50.00"))

    def test_purchase_after_closing_day_goes_to_next_statement(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            card=self.credit_card,
            day=25,
        )

        confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertEqual((forecast.statement.year, forecast.statement.month), (2026, 7))

    def test_card_purchase_with_recurrence_account_clears_account(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            card=self.credit_card,
            account=self.account,
        )

        confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertIsNone(forecast.account)

    def test_income_recurrence_becomes_income(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.INCOME, account=self.account
        )

        confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertEqual(forecast.transaction_type, Transaction.TransactionType.INCOME)
        self.assertEqual(forecast.status, Transaction.PaymentStatus.PENDING)
        self.assertIsNone(forecast.statement)

    def test_fixed_bill_without_card_becomes_expense(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL, account=self.account
        )

        confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertEqual(forecast.transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertIsNone(forecast.statement)

    def test_balance_card_recurrence_is_rejected_without_changes(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            card=self.benefit_card,
        )

        with self.assertRaises(ValidationError) as ctx:
            confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertIn("crédito", ctx.exception.messages[0])
        self.assertEqual(forecast.transaction_type, Transaction.TransactionType.FORECAST)
        self.assertEqual(forecast.status, Transaction.PaymentStatus.FORECASTED)

    def test_paid_statement_rejects_confirmation_without_changes(self):
        forecast = self._forecast(
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            card=self.credit_card,
        )
        CardStatement.objects.create(
            card=self.credit_card,
            year=2026,
            month=6,
            closing_date=date(2026, 6, 20),
            due_date=date(2026, 6, 27),
            status=CardStatement.StatementStatus.PAID,
            payment_account=self.account,
        )

        with self.assertRaises(ValidationError):
            confirm_forecast(forecast=forecast)
        forecast.refresh_from_db()

        self.assertEqual(forecast.transaction_type, Transaction.TransactionType.FORECAST)
        self.assertIsNone(forecast.statement)
