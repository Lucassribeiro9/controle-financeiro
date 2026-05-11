"""Tests dos serviços do app transactions."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction
from transactions.services import create_transaction, create_transfer, mark_transaction_as_paid


class TransactionServiceTests(TestCase):
    """Garante as regras de negocio para criacao de transacoes."""

    def setUp(self):
        """Cria dados base para os cenarios de transacao."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )

    def test_create_income_increases_account_balance(self):
        """Deve aumentar o saldo da conta ao criar uma receita."""

        transaction = create_transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertIsNotNone(transaction.id)
        self.assertEqual(self.account.balance, Decimal("6000.00"))

    def test_create_expense_decreases_account_balance(self):
        """Deve reduzir o saldo da conta ao criar uma despesa."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertIsNotNone(transaction.id)
        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_create_statement_payment_decreases_account_balance(self):
        """Deve reduzir saldo da conta ao registrar pagamento de fatura."""

        create_transaction(
            description="Pagamento fatura",
            amount=Decimal("400.00"),
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            account=self.account,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("600.00"))

    def test_create_forecast_does_not_change_account_balance(self):
        """Nao deve alterar saldo ao criar uma previsao."""

        create_transaction(
            description="Internet prevista",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_create_card_purchase_does_not_change_payment_account_balance(self):
        """Nao deve alterar saldo da conta ao criar compra no cartao."""

        create_transaction(
            description="Compra no cartao",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.card,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_mark_transaction_as_paid_updates_status(self):
        """Deve marcar uma transacao como paga."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        paid_transaction = mark_transaction_as_paid(transaction.id)

        self.assertEqual(paid_transaction.status, Transaction.PaymentStatus.PAID)

    def test_mark_transaction_as_paid_does_not_apply_balance_twice(self):
        """Nao deve alterar saldo novamente ao marcar transacao como paga."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )
        self.account.refresh_from_db()
        balance_after_creation = self.account.balance

        mark_transaction_as_paid(transaction.id)

        self.account.refresh_from_db()

        self.assertEqual(balance_after_creation, Decimal("750.00"))
        self.assertEqual(self.account.balance, balance_after_creation)

    def test_mark_paid_transaction_as_paid_is_idempotent(self):
        """Nao deve alterar saldo ao marcar como paga uma transacao ja paga."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        mark_transaction_as_paid(transaction.id)
        mark_transaction_as_paid(transaction.id)

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("750.00"))


class TransferServiceTests(TestCase):
    """Garante as regras de negócio para criação de transferências."""

    def setUp(self):
        """Cria contas base para os cenarios de transferencia."""

        self.institution = Institution.objects.create(name="Inter", code="077")

        self.source_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

        self.destination_account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("200.00"),
        )

    def test_create_valid_transfer(self):
        """Deve criar transferencia valida usando o servico."""

        transfer = create_transfer(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        self.assertIsNotNone(transfer.id)
        self.assertEqual(transfer.amount, Decimal("300.00"))
        self.assertEqual(transfer.from_account, self.source_account)
        self.assertEqual(transfer.destination_account, self.destination_account)

    def test_create_transfer_moves_balance_between_accounts(self):
        """Deve reduzir origem e aumentar destino ao criar transferencia."""

        create_transfer(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        self.source_account.refresh_from_db()
        self.destination_account.refresh_from_db()

        self.assertEqual(self.source_account.balance, Decimal("700.00"))
        self.assertEqual(self.destination_account.balance, Decimal("500.00"))
