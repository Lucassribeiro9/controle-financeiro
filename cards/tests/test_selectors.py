"""Tests dos selectors do app cards."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.selectors import get_card_limits, get_statement_summary
from institutions.models import Institution
from transactions.models import Transaction


class CardLimitSelectorTests(TestCase):
    """Garante o calculo dinamico de limite de cartao de credito."""

    def setUp(self):
        """Cria dados base para cenarios de limite."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.payment_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )

    def test_card_without_transactions_returns_full_available_limit(self):
        """Cartao sem compras deve manter limite disponivel integral."""

        limits = get_card_limits(self.card)

        self.assertEqual(limits["credit_limit"], Decimal("5000.00"))
        self.assertEqual(limits["used_limit"], Decimal("0.00"))
        self.assertEqual(limits["available_limit"], Decimal("5000.00"))
        self.assertIsInstance(limits["credit_limit"], Decimal)
        self.assertIsInstance(limits["used_limit"], Decimal)
        self.assertIsInstance(limits["available_limit"], Decimal)

    def test_open_statement_card_purchases_reduce_available_limit(self):
        """Compras em fatura aberta devem consumir limite."""

        statement = self._create_statement(status=CardStatement.StatementStatus.OPEN)
        self._create_card_purchase(
            amount=Decimal("350.00"),
            statement=statement,
        )
        self._create_card_purchase(
            amount=Decimal("150.00"),
            statement=statement,
        )

        limits = get_card_limits(self.card)

        self.assertEqual(limits["used_limit"], Decimal("500.00"))
        self.assertEqual(limits["available_limit"], Decimal("4500.00"))

    def test_future_installments_reduce_available_limit(self):
        """Parcelas futuras em faturas nao pagas devem consumir o limite total."""

        current_statement = self._create_statement(
            month=5,
            status=CardStatement.StatementStatus.OPEN,
        )
        future_statement = self._create_statement(
            month=6,
            status=CardStatement.StatementStatus.FORECASTED,
        )
        self._create_card_purchase(
            amount=Decimal("100.00"),
            statement=current_statement,
            installment_number=1,
        )
        self._create_card_purchase(
            amount=Decimal("100.00"),
            statement=future_statement,
            installment_number=2,
            transaction_date=date(2026, 6, 8),
        )

        limits = get_card_limits(self.card)

        self.assertEqual(limits["used_limit"], Decimal("200.00"))
        self.assertEqual(limits["available_limit"], Decimal("4800.00"))

    def test_canceled_transaction_does_not_affect_limit(self):
        """Compra cancelada nao deve consumir limite."""

        statement = self._create_statement(status=CardStatement.StatementStatus.OPEN)
        self._create_card_purchase(
            amount=Decimal("300.00"),
            statement=statement,
            status=Transaction.PaymentStatus.CANCELED,
        )

        limits = get_card_limits(self.card)

        self.assertEqual(limits["used_limit"], Decimal("0.00"))
        self.assertEqual(limits["available_limit"], Decimal("5000.00"))

    def test_ignored_transaction_does_not_affect_limit(self):
        """Compra ignorada nao deve consumir limite."""

        statement = self._create_statement(status=CardStatement.StatementStatus.OPEN)
        self._create_card_purchase(
            amount=Decimal("300.00"),
            statement=statement,
            status=Transaction.PaymentStatus.IGNORED,
        )

        limits = get_card_limits(self.card)

        self.assertEqual(limits["used_limit"], Decimal("0.00"))
        self.assertEqual(limits["available_limit"], Decimal("5000.00"))

    def test_paid_statement_releases_limit(self):
        """Fatura paga deve liberar o limite das compras vinculadas."""

        paid_statement = self._create_statement(status=CardStatement.StatementStatus.PAID)
        open_statement = self._create_statement(
            month=6,
            status=CardStatement.StatementStatus.OPEN,
        )
        self._create_card_purchase(
            amount=Decimal("400.00"),
            statement=paid_statement,
        )
        self._create_card_purchase(
            amount=Decimal("125.00"),
            statement=open_statement,
            transaction_date=date(2026, 6, 8),
        )

        limits = get_card_limits(self.card)

        self.assertEqual(limits["used_limit"], Decimal("125.00"))
        self.assertEqual(limits["available_limit"], Decimal("4875.00"))

    def _create_statement(
        self,
        *,
        month=5,
        status=CardStatement.StatementStatus.OPEN,
    ):
        """Cria uma fatura do cartao base."""

        return CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=month,
            closing_date=date(2026, month, 20),
            due_date=date(2026, month, 27),
            status=status,
            payment_account=self.payment_account,
        )

    def _create_card_purchase(
        self,
        *,
        amount,
        statement,
        status=Transaction.PaymentStatus.PENDING,
        installment_number=None,
        transaction_date=date(2026, 5, 8),
    ):
        """Cria uma compra de cartao vinculada a uma fatura."""

        return Transaction.objects.create(
            description="Compra no cartão",
            amount=amount,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=status,
            card=self.card,
            statement=statement,
            installment_number=installment_number,
            date=transaction_date,
        )


class CardStatementSummarySelectorTests(TestCase):
    """Garante o resumo da fatura na tela de detalhe."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.payment_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )

    def test_statement_summary_returns_expected_closed_paid_and_remaining_amounts(self):
        """Resumo deve refletir os valores atuais da fatura."""

        statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=5,
            expected_amount=Decimal("500.00"),
            closed_amount=Decimal("420.00"),
            paid_amount=Decimal("150.00"),
            closing_date=date(2026, 5, 20),
            due_date=date(2026, 5, 27),
            status=CardStatement.StatementStatus.PARTIALLY_PAID,
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("500.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=date(2026, 5, 8),
        )

        summary = get_statement_summary(statement)

        self.assertEqual(summary["expected_amount"], Decimal("500.00"))
        self.assertEqual(summary["closed_amount"], Decimal("420.00"))
        self.assertEqual(summary["paid_amount"], Decimal("150.00"))
        self.assertEqual(summary["remaining_amount"], Decimal("270.00"))
        self.assertEqual(summary["status"], CardStatement.StatementStatus.PARTIALLY_PAID)
        self.assertFalse(summary["is_fully_paid"])

    def test_open_statement_summary_uses_linked_purchase_total(self):
        """Fatura aberta deve mostrar o total das compras vinculadas como previsto."""

        statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=5,
            closing_date=date(2026, 5, 20),
            due_date=date(2026, 5, 27),
            status=CardStatement.StatementStatus.OPEN,
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=date(2026, 5, 8),
        )

        summary = get_statement_summary(statement)

        self.assertEqual(summary["expected_amount"], Decimal("350.00"))
        self.assertEqual(summary["closed_amount"], Decimal("350.00"))
        self.assertEqual(summary["remaining_amount"], Decimal("350.00"))
        self.assertFalse(summary["is_fully_paid"])

    def test_paid_statement_summary_marks_fully_paid(self):
        """Fatura paga deve marcar o resumo como totalmente quitado."""

        statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=5,
            expected_amount=Decimal("500.00"),
            closed_amount=Decimal("420.00"),
            paid_amount=Decimal("420.00"),
            closing_date=date(2026, 5, 20),
            due_date=date(2026, 5, 27),
            status=CardStatement.StatementStatus.PAID,
            payment_account=self.payment_account,
        )

        summary = get_statement_summary(statement)

        self.assertEqual(summary["remaining_amount"], Decimal("0.00"))
        self.assertTrue(summary["is_fully_paid"])
