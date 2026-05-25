"""Tests das views do app cards."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.services import close_statement
from institutions.models import Institution
from transactions.models import Transaction


class CardViewTests(TestCase):
    """Garante telas de listagem, criacao e edicao de cartoes."""

    def setUp(self):
        """Cria dados base para os cenarios."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.payment_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

    def test_card_list_page_returns_success(self):
        """Deve renderizar a lista de cartoes."""

        Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )

        response = self.client.get(reverse("cards:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/list.html")
        self.assertContains(response, "Inter Gold")
        self.assertContains(response, "Inter")
        self.assertContains(response, "Crédito")
        self.assertContains(response, "Conta corrente")

    def test_card_create_page_returns_form(self):
        """Deve renderizar formulario de criacao de cartao."""

        response = self.client.get(reverse("cards:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/form.html")
        self.assertContains(response, "Novo cartão")

    def test_post_create_valid_credit_card(self):
        """Deve criar cartao de credito valido."""

        response = self.client.post(
            reverse("cards:create"),
            data={
                "name": "Inter Gold",
                "institution": self.institution.id,
                "card_type": Card.CardType.CREDIT,
                "credit_limit": "5000.00",
                "statement_closing_day": "20",
                "statement_due_day": "27",
                "payment_account": self.payment_account.id,
                "estimated_balance": "",
                "is_active": "on",
            },
        )
        card = Card.objects.get(name="Inter Gold")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("cards:list"))
        self.assertEqual(card.card_type, Card.CardType.CREDIT)
        self.assertEqual(card.credit_limit, Decimal("5000.00"))
        self.assertEqual(card.payment_account, self.payment_account)

    def test_post_create_valid_benefit_card(self):
        """Deve criar cartao de beneficio valido."""

        response = self.client.post(
            reverse("cards:create"),
            data={
                "name": "Caju VA",
                "institution": self.institution.id,
                "card_type": Card.CardType.BENEFIT,
                "credit_limit": "",
                "statement_closing_day": "",
                "statement_due_day": "",
                "payment_account": "",
                "estimated_balance": "850.00",
                "is_active": "on",
            },
        )
        card = Card.objects.get(name="Caju VA")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(card.card_type, Card.CardType.BENEFIT)
        self.assertEqual(card.estimated_balance, Decimal("850.00"))

    def test_post_update_card_edits_card(self):
        """Deve editar um cartao cadastrado."""

        card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )

        response = self.client.post(
            reverse("cards:update", kwargs={"card_id": card.id}),
            data={
                "name": "Inter Platinum",
                "institution": self.institution.id,
                "card_type": Card.CardType.CREDIT,
                "credit_limit": "7000.00",
                "statement_closing_day": "18",
                "statement_due_day": "25",
                "payment_account": self.payment_account.id,
                "estimated_balance": "",
                "is_active": "on",
            },
        )
        card.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(card.name, "Inter Platinum")
        self.assertEqual(card.credit_limit, Decimal("7000.00"))
        self.assertEqual(card.statement_closing_day, 18)


class StatementViewTests(TestCase):
    """Garante telas de faturas e pagamento via service."""

    def setUp(self):
        """Cria dados base para cenarios de fatura."""

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

    def test_statement_list_page_returns_success(self):
        """Deve renderizar a lista de faturas."""

        statement = self._create_statement()

        response = self.client.get(reverse("cards:statements"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/statements.html")
        self.assertContains(response, self.card.name)
        self.assertContains(response, f"{statement.month}/{statement.year}")
        self.assertContains(response, "Pendente")
        self.assertContains(response, 'class="badge badge-warning"', html=False)

    def test_statement_detail_page_returns_success(self):
        """Deve renderizar detalhe da fatura."""

        statement = self._create_statement()

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/statement_detail.html")
        self.assertContains(response, self.card.name)
        self.assertContains(response, "Valor fechado")

    def test_post_pay_statement_pays_statement(self):
        """Deve pagar fatura via POST usando pay_statement."""

        statement = self._create_statement(amount=Decimal("350.00"))

        response = self.client.post(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id}),
            data={"amount": ""},
        )
        statement.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id}),
        )
        self.assertEqual(statement.status, CardStatement.StatementStatus.PAID)
        self.assertEqual(statement.paid_amount, Decimal("350.00"))

    def test_post_pay_statement_decreases_payment_account_balance(self):
        """Pagamento deve reduzir saldo da conta de pagamento."""

        statement = self._create_statement(amount=Decimal("350.00"))

        self.client.post(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id}),
            data={"amount": ""},
        )
        self.payment_account.refresh_from_db()

        self.assertEqual(self.payment_account.balance, Decimal("650.00"))

    def test_post_pay_statement_does_not_duplicate_expense(self):
        """Pagamento nao deve criar despesa comum nem aplicar impacto duplicado."""

        statement = self._create_statement(amount=Decimal("350.00"))

        self.client.post(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id}),
            data={"amount": ""},
        )
        self.payment_account.refresh_from_db()

        self.assertEqual(self.payment_account.balance, Decimal("650.00"))
        self.assertEqual(
            Transaction.objects.filter(
                transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
                statement=statement,
            ).count(),
            1,
        )
        self.assertFalse(
            Transaction.objects.filter(
                transaction_type=Transaction.TransactionType.EXPENSE,
                statement=statement,
            ).exists()
        )

    def _create_statement(self, *, amount=Decimal("250.00")):
        """Cria uma fatura fechada com compra vinculada."""

        statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=5,
            expected_amount=amount,
            closing_date=date(2026, 5, 20),
            due_date=date(2026, 5, 27),
            payment_account=self.payment_account,
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
