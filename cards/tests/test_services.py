"""Tests dos servicos do app cards."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.services import close_statement, get_or_create_card_statement, pay_statement
from institutions.models import Institution
from transactions.models import Transaction


class CardStatementServiceTests(TestCase):
    """Garante as regras de negocio para faturas de cartao."""

    def setUp(self):
        """Cria dados base para os cenarios de fatura."""

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

    def test_purchase_before_or_on_closing_day_uses_current_month_statement(self):
        """Compra antes ou no fechamento deve entrar na fatura do mes atual."""

        statement_before_closing = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 18),
        )
        statement_on_closing = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 20),
        )

        self.assertEqual(statement_before_closing.month, 5)
        self.assertEqual(statement_before_closing.year, 2026)
        self.assertEqual(statement_on_closing, statement_before_closing)

    def test_purchase_after_closing_day_uses_next_month_statement(self):
        """Compra depois do fechamento deve entrar na proxima fatura."""

        statement = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 21),
        )

        self.assertEqual(statement.month, 6)
        self.assertEqual(statement.year, 2026)
        self.assertEqual(statement.closing_date, date(2026, 6, 20))
        self.assertEqual(statement.due_date, date(2026, 6, 27))

    def test_created_statement_inherits_card_payment_account(self):
        """Fatura criada deve herdar a conta de pagamento padrao do cartao."""

        statement = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 8),
        )

        self.assertEqual(statement.payment_account, self.payment_account)

    def test_close_statement_sums_linked_card_purchases_and_marks_pending(self):
        """Fechar fatura deve somar compras vinculadas e marcar como pendente."""

        statement = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Internet",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=date(2026, 5, 10),
        )

        closed_statement = close_statement(statement=statement)

        self.assertEqual(closed_statement.closed_amount, Decimal("350.00"))
        self.assertEqual(closed_statement.status, CardStatement.StatementStatus.PENDING)

    def test_close_statement_does_not_change_payment_account_balance(self):
        """Fechar fatura nao deve alterar saldo da conta de pagamento."""

        statement = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=date(2026, 5, 8),
        )

        close_statement(statement=statement)
        self.payment_account.refresh_from_db()

        self.assertEqual(self.payment_account.balance, Decimal("1000.00"))

    def test_pay_statement_decreases_payment_account_balance(self):
        """Pagar fatura deve reduzir saldo da conta de pagamento."""

        statement = self._create_closed_statement(amount=Decimal("350.00"))

        paid_statement = pay_statement(statement=statement)
        self.payment_account.refresh_from_db()

        self.assertEqual(paid_statement.status, CardStatement.StatementStatus.PAID)
        self.assertEqual(self.payment_account.balance, Decimal("650.00"))

    def test_pay_statement_locks_payment_account_before_debit(self):
        """Pagar fatura deve bloquear a conta antes de debitar o saldo."""

        statement = self._create_closed_statement(amount=Decimal("350.00"))

        with patch(
            "cards.services.FinancialAccount.objects.select_for_update",
            wraps=FinancialAccount.objects.select_for_update,
        ) as select_for_update:
            pay_statement(statement=statement)

        select_for_update.assert_called_once()

    def test_pay_statement_creates_statement_payment_transaction(self):
        """Pagar fatura deve criar transacao do tipo pagamento de fatura."""

        statement = self._create_closed_statement(amount=Decimal("350.00"))

        pay_statement(statement=statement)

        payment_transaction = Transaction.objects.get(
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            statement=statement,
        )
        self.assertEqual(payment_transaction.amount, Decimal("350.00"))
        self.assertEqual(payment_transaction.status, Transaction.PaymentStatus.PAID)
        self.assertEqual(payment_transaction.account, self.payment_account)
        self.assertEqual(payment_transaction.card, self.card)

    def test_partial_payment_marks_statement_as_partially_paid(self):
        """Pagamento parcial deve marcar fatura como parcialmente paga."""

        statement = self._create_closed_statement(amount=Decimal("350.00"))

        paid_statement = pay_statement(statement=statement, amount=Decimal("150.00"))
        self.payment_account.refresh_from_db()

        self.assertEqual(paid_statement.paid_amount, Decimal("150.00"))
        self.assertEqual(
            paid_statement.status,
            CardStatement.StatementStatus.PARTIALLY_PAID,
        )
        self.assertEqual(self.payment_account.balance, Decimal("850.00"))

    def test_full_payment_marks_statement_as_paid(self):
        """Pagamento total deve marcar fatura como paga."""

        statement = self._create_closed_statement(amount=Decimal("350.00"))

        paid_statement = pay_statement(statement=statement, amount=Decimal("350.00"))

        self.assertEqual(paid_statement.paid_amount, Decimal("350.00"))
        self.assertEqual(paid_statement.status, CardStatement.StatementStatus.PAID)

    def _create_closed_statement(self, *, amount):
        """Cria uma fatura fechada com uma compra vinculada."""

        statement = get_or_create_card_statement(
            card=self.card,
            transaction_date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=amount,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=date(2026, 5, 8),
        )

        return close_statement(statement=statement)
