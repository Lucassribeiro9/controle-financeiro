"""Tests dos forms do app transactions."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from institutions.models import Institution
from transactions.forms import TransactionForm, TransferForm
from transactions.models import Transaction


class TransactionFormTests(TestCase):
    """Garante o contrato dinamico do formulario de lancamentos."""

    def setUp(self):
        """Cria dados base para os cenarios do form."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.destination_account = FinancialAccount.objects.create(
            name="Conta reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")
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
            estimated_balance=Decimal("300.00"),
            balance=Decimal("300.00"),
        )

    def test_transaction_form_exposes_payment_method(self):
        """O form deve expor a forma de pagamento como campo principal."""

        form = TransactionForm()

        self.assertIn("payment_method", form.fields)
        self.assertEqual(
            form.fields["payment_method"].choices[0][0],
            "debit",
        )

    def test_debit_requires_account(self):
        """Debito deve exigir conta financeira."""

        form = TransactionForm(
            data={
                "description": "Mercado",
                "payment_method": "debit",
                "amount": "250.00",
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "status": Transaction.PaymentStatus.PAID,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("account", form.errors)

    def test_credit_requires_card_and_card_purchase_type(self):
        """Credito deve exigir cartao e compra no cartao."""

        form = TransactionForm(
            data={
                "description": "Compra online",
                "payment_method": "credit",
                "amount": "120.00",
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "status": Transaction.PaymentStatus.PENDING,
                "account": self.account.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("card", form.errors)
        self.assertIn("transaction_type", form.errors)

    def test_credit_allows_inline_installment_count(self):
        """Credito deve aceitar quantidade de parcelas maior que uma."""

        form = TransactionForm(
            data={
                "description": "Notebook",
                "payment_method": "credit",
                "amount": "1000.00",
                "transaction_type": Transaction.TransactionType.CARD_PURCHASE,
                "status": Transaction.PaymentStatus.PENDING,
                "card": self.credit_card.id,
                "total_installments": "10",
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_credit_rejects_single_installment(self):
        """Credito nao deve aceitar parcela unica como parcelamento inline."""

        form = TransactionForm(
            data={
                "description": "Notebook",
                "payment_method": "credit",
                "amount": "1000.00",
                "transaction_type": Transaction.TransactionType.CARD_PURCHASE,
                "status": Transaction.PaymentStatus.PENDING,
                "card": self.credit_card.id,
                "total_installments": "1",
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("total_installments", form.errors)

    def test_benefit_requires_benefit_card(self):
        """Beneficio deve exigir cartao de beneficio."""

        form = TransactionForm(
            data={
                "description": "Almoco",
                "payment_method": "benefit",
                "amount": "35.00",
                "transaction_type": Transaction.TransactionType.BENEFIT_PURCHASE,
                "status": Transaction.PaymentStatus.PENDING,
                "account": self.account.id,
                "card": self.credit_card.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("card", form.errors)

    def test_benefit_requires_benefit_purchase_type(self):
        """Beneficio deve usar tipo proprio de compra de beneficio."""

        form = TransactionForm(
            data={
                "description": "Almoco",
                "payment_method": "benefit",
                "amount": "35.00",
                "transaction_type": Transaction.TransactionType.CARD_PURCHASE,
                "status": Transaction.PaymentStatus.PENDING,
                "card": self.benefit_card.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("transaction_type", form.errors)

    def test_benefit_allows_benefit_purchase_type(self):
        """Beneficio deve aceitar compra de beneficio com cartao de beneficio."""

        form = TransactionForm(
            data={
                "description": "Almoco",
                "payment_method": "benefit",
                "amount": "35.00",
                "transaction_type": Transaction.TransactionType.BENEFIT_PURCHASE,
                "status": Transaction.PaymentStatus.PENDING,
                "card": self.benefit_card.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_transfer_requires_different_accounts(self):
        """Transferencia deve exigir origem e destino diferentes."""

        form = TransactionForm(
            data={
                "description": "Aporte",
                "payment_method": "transfer",
                "amount": "100.00",
                "transaction_type": Transaction.TransactionType.ADJUSTMENT,
                "status": Transaction.PaymentStatus.PENDING,
                "from_account": self.account.id,
                "destination_account": self.account.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("destination_account", form.errors)

    def test_cash_allows_regular_account_based_lancamento(self):
        """Dinheiro/outro deve aceitar conta para lancamentos comuns."""

        form = TransactionForm(
            data={
                "description": "Dinheiro",
                "payment_method": "cash",
                "amount": "50.00",
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "status": Transaction.PaymentStatus.PAID,
                "account": self.account.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)


class TransferFormTests(TestCase):
    """Mantem o contrato do formulario de transferencias."""

    def setUp(self):
        """Cria contas base para o form."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.destination_account = FinancialAccount.objects.create(
            name="Conta reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )

    def test_transfer_form_requires_different_accounts(self):
        """TransferForm segue exigindo contas distintas."""

        form = TransferForm(
            data={
                "description": "Aporte",
                "amount": "100.00",
                "from_account": self.account.id,
                "destination_account": self.account.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("destination_account", form.errors)
