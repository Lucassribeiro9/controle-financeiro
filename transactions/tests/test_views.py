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
from transactions.models import Transaction, Transfer


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
        self.assertContains(response, "Novo lançamento")

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
        self.assertContains(response, "Lançamento exige conta financeira.")
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


class TransferViewTests(TestCase):
    """Garante telas de listagem e criacao de transferencias."""

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

    def test_transfer_list_page_returns_success(self):
        """Deve renderizar a lista de transferencias."""

        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        response = self.client.get(
            reverse("transactions:transfers"),
            data={"year": 2026, "month": 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/transfers.html")
        self.assertContains(response, "Aporte reserva")
        self.assertContains(response, "Conta corrente")
        self.assertContains(response, "Porquinho reserva")

    def test_transfer_list_page_uses_current_period_by_default(self):
        """Deve usar periodo atual quando query string nao informar periodo."""

        today = timezone.localdate()

        response = self.client.get(reverse("transactions:transfers"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], today.year)
        self.assertEqual(response.context["month"], today.month)

    def test_transfer_create_page_returns_form(self):
        """Deve renderizar formulario de transferencia."""

        response = self.client.get(reverse("transactions:transfer-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/transfer_form.html")
        self.assertContains(response, "Nova transferência")

    def test_post_create_transfer_uses_service(self):
        """Deve criar transferencia usando o service."""

        response = self.client.post(
            reverse("transactions:transfer-create"),
            data={
                "description": "Aporte reserva",
                "amount": "300.00",
                "from_account": self.source_account.id,
                "destination_account": self.destination_account.id,
                "date": "2026-05-08",
                "notes": "Reserva mensal",
            },
        )
        transfer = Transfer.objects.get(description="Aporte reserva")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("transactions:transfers"))
        self.assertEqual(transfer.amount, Decimal("300.00"))
        self.assertEqual(transfer.notes, "Reserva mensal")
        self.assertEqual(Transaction.objects.count(), 0)

    def test_post_create_transfer_updates_balances(self):
        """Deve reduzir origem e aumentar destino."""

        self.client.post(
            reverse("transactions:transfer-create"),
            data={
                "description": "Aporte reserva",
                "amount": "300.00",
                "from_account": self.source_account.id,
                "destination_account": self.destination_account.id,
                "date": "2026-05-08",
                "notes": "",
            },
        )
        self.source_account.refresh_from_db()
        self.destination_account.refresh_from_db()

        self.assertEqual(self.source_account.balance, Decimal("700.00"))
        self.assertEqual(self.destination_account.balance, Decimal("500.00"))

    def test_post_create_transfer_rejects_same_source_and_destination(self):
        """Nao deve permitir mesma conta de origem e destino."""

        response = self.client.post(
            reverse("transactions:transfer-create"),
            data={
                "description": "Transferencia invalida",
                "amount": "300.00",
                "from_account": self.source_account.id,
                "destination_account": self.source_account.id,
                "date": "2026-05-08",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/transfer_form.html")
        self.assertContains(
            response,
            "Conta de destino deve ser diferente da conta de origem.",
        )
        self.assertEqual(Transfer.objects.count(), 0)
