"""Tests dos models do app transactions."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction, Transfer


class TransactionModelTests(TestCase):
    """Garante as regras principais do model Transaction."""

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

    def test_create_income_transaction_linked_to_account(self):
        """Deve criar receita vinculada a uma conta financeira."""

        transaction = Transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )
        transaction.full_clean()
        transaction.save()

        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.INCOME)
        self.assertEqual(transaction.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(transaction.account, self.account)

    def test_create_expense_transaction_linked_to_account_and_category(self):
        """Deve criar despesa vinculada a conta e categoria."""

        transaction = Transaction(
            description="Mercado",
            amount=Decimal("250.75"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )
        transaction.full_clean()
        transaction.save()

        self.assertEqual(transaction.category, self.category)
        self.assertEqual(transaction.amount, Decimal("250.75"))

    def test_create_card_purchase_requires_card(self):
        """Deve exigir cartao para transacao de compra no cartao."""

        transaction = Transaction(
            description="Compra online",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            date=date(2026, 5, 8),
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_create_card_purchase_with_card(self):
        """Deve permitir compra no cartao quando ha cartao vinculado."""

        transaction = Transaction(
            description="Assinatura",
            amount=Decimal("39.90"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.card,
            category=self.category,
            date=date(2026, 5, 8),
        )
        transaction.full_clean()
        transaction.save()

        self.assertEqual(transaction.card, self.card)
        self.assertIsNone(transaction.account)

    def test_transaction_amount_must_be_positive(self):
        """Nao deve validar transacao com valor zero ou negativo."""

        transaction = Transaction(
            description="Valor invalido",
            amount=Decimal("0.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_str_returns_description_and_amount(self):
        """O __str__ deve retornar descricao e valor da transacao."""

        transaction = Transaction(
            description="Internet",
            amount=Decimal("99.90"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )

        self.assertEqual(str(transaction), "Internet - 99.90")


class TransferModelTests(TestCase):
    """Garante as regras principais do model Transfer."""

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

    def test_create_transfer_between_different_accounts(self):
        """Deve criar transferencia entre contas financeiras diferentes."""

        transfer = Transfer(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )
        transfer.full_clean()
        transfer.save()

        self.assertEqual(transfer.from_account, self.source_account)
        self.assertEqual(transfer.destination_account, self.destination_account)

    def test_transfer_amount_must_be_positive(self):
        """Nao deve validar transferencia com valor zero ou negativo."""

        transfer = Transfer(
            description="Transferencia invalida",
            amount=Decimal("-10.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        with self.assertRaises(ValidationError):
            transfer.full_clean()

    def test_transfer_destination_must_be_different_from_source(self):
        """Nao deve permitir transferencia para a mesma conta."""

        transfer = Transfer(
            description="Mesma conta",
            amount=Decimal("50.00"),
            from_account=self.source_account,
            destination_account=self.source_account,
            date=date(2026, 5, 8),
        )

        with self.assertRaises(ValidationError):
            transfer.full_clean()

    def test_transfer_is_not_a_transaction(self):
        """Transferencia interna nao deve criar receita nem despesa."""

        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        self.assertEqual(Transaction.objects.count(), 0)

    def test_str_returns_origin_destination_and_amount(self):
        """O __str__ deve retornar origem, destino e valor da transferencia."""

        transfer = Transfer(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        expected = "Conta corrente (Inter) -> Porquinho reserva (Inter) - 300.00"
        self.assertEqual(str(transfer), expected)
