"""Tests das views do app transactions."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction


class TransactionViewTests(TestCase):
    """Garante telas de listagem, criacao e detalhe de lancamentos."""

    def setUp(self):
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

    def test_transaction_list_page_returns_success(self):
        """Deve renderizar a lista de lancamentos."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        response = self.client.get(
            reverse("transactions:list"),
            data={"year": 2026, "month": 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/list.html")
        self.assertContains(response, "Mercado")

    def test_transaction_list_page_uses_current_period_by_default(self):
        """Deve usar o periodo atual quando a query string nao informar periodo."""

        today = timezone.localdate()

        response = self.client.get(reverse("transactions:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], today.year)
        self.assertEqual(response.context["month"], today.month)

    def test_transaction_create_page_returns_form(self):
        """Deve renderizar o formulario de criacao."""

        response = self.client.get(reverse("transactions:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/form.html")
        self.assertContains(response, "Novo lancamento")

    def test_post_create_income_uses_service_and_increases_balance(self):
        """Deve criar receita via service e aumentar saldo da conta."""

        response = self.client.post(
            reverse("transactions:create"),
            data={
                "description": "Salario",
                "amount": "5000.00",
                "transaction_type": Transaction.TransactionType.INCOME,
                "status": Transaction.PaymentStatus.PAID,
                "account": self.account.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            },
        )

        self.account.refresh_from_db()
        transaction = Transaction.objects.get(description="Salario")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("transactions:detail", kwargs={"transaction_id": transaction.id}))
        self.assertEqual(self.account.balance, Decimal("6000.00"))

    def test_post_create_expense_uses_service_and_decreases_balance(self):
        """Deve criar despesa via service e reduzir saldo da conta."""

        response = self.client.post(
            reverse("transactions:create"),
            data={
                "description": "Mercado",
                "amount": "250.00",
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "status": Transaction.PaymentStatus.PAID,
                "account": self.account.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            },
        )

        self.account.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transaction.objects.get(description="Mercado").amount, Decimal("250.00"))
        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_post_create_card_purchase_does_not_decrease_account_balance(self):
        """Compra no cartao nao deve reduzir saldo da conta no cadastro."""

        response = self.client.post(
            reverse("transactions:create"),
            data={
                "description": "Compra no cartao",
                "amount": "120.00",
                "transaction_type": Transaction.TransactionType.CARD_PURCHASE,
                "status": Transaction.PaymentStatus.PENDING,
                "card": self.card.id,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            },
        )

        self.account.refresh_from_db()
        transaction = Transaction.objects.get(description="Compra no cartao")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(transaction.card, self.card)
        self.assertIsNone(transaction.account)
        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_post_create_expense_without_account_shows_form_error(self):
        """Formulario invalido deve mostrar erro sem criar transacao."""

        response = self.client.post(
            reverse("transactions:create"),
            data={
                "description": "Mercado",
                "amount": "250.00",
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "status": Transaction.PaymentStatus.PAID,
                "category": self.category.id,
                "date": "2026-05-08",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/form.html")
        self.assertContains(response, "Lancamento exige conta financeira.")
        self.assertEqual(Transaction.objects.count(), 0)

    def test_transaction_detail_page_returns_success(self):
        """Deve renderizar detalhe de um lancamento."""

        transaction = Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        response = self.client.get(
            reverse("transactions:detail", kwargs={"transaction_id": transaction.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/detail.html")
        self.assertContains(response, "Mercado")
