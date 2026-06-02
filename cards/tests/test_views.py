"""Tests das views do app cards."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.services import close_statement
from cards.selectors import get_card_limits
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

    def test_card_list_page_shows_credit_limit_summary(self):
        """Deve mostrar limite usado, disponivel e total de cartao de credito."""

        card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )
        statement = CardStatement.objects.create(
            card=card,
            year=2026,
            month=5,
            closing_date="2026-05-20",
            due_date="2026-05-27",
        )
        Transaction.objects.create(
            description="Compra no cartao",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=card,
            statement=statement,
            date="2026-05-08",
        )

        response = self.client.get(reverse("cards:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5.000,00")
        self.assertContains(response, "350,00")
        self.assertContains(response, "4.650,00")
        self.assertContains(response, 'class="limit-bar"', html=False)

        limits = get_card_limits(card)
        self.assertEqual(limits["credit_limit"], Decimal("5000.00"))
        self.assertEqual(limits["used_limit"], Decimal("350.00"))
        self.assertEqual(limits["available_limit"], Decimal("4650.00"))

    def test_card_list_page_marks_overlimit_cards(self):
        """Deve exibir alerta visual quando limite estiver excedido."""

        card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("100.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )
        statement = CardStatement.objects.create(
            card=card,
            year=2026,
            month=5,
            closing_date="2026-05-20",
            due_date="2026-05-27",
        )
        Transaction.objects.create(
            description="Compra no cartao",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=card,
            statement=statement,
            date="2026-05-08",
        )

        response = self.client.get(reverse("cards:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Limite excedido")
        self.assertContains(response, 'class="limit-bar-fill limit-bar-over"', html=False)

    def test_card_list_page_does_not_show_credit_summary_for_non_credit_cards(self):
        """Cartoes nao credito nao devem mostrar indicadores de limite de credito."""

        Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("850.00"),
            balance=Decimal("850.00"),
        )

        response = self.client.get(reverse("cards:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não se aplica")
        self.assertNotContains(response, 'class="limit-bar"', html=False)

    def test_card_create_page_returns_form(self):
        """Deve renderizar formulario de criacao de cartao."""

        response = self.client.get(reverse("cards:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/form.html")
        self.assertContains(response, "Novo cartão")
        self.assertContains(response, 'data-conditional-form="card"', html=False)
        self.assertContains(response, 'data-conditional-source="card-type"', html=False)
        self.assertContains(response, 'data-conditional-field="card-credit"', html=False)
        self.assertContains(response, 'data-conditional-field="card-balance"', html=False)
        self.assertContains(response, "js/app.js")

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
        self.assertEqual(card.balance, Decimal("850.00"))

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

    def test_post_update_benefit_card_updates_real_balance(self):
        """Deve atualizar saldo real do beneficio pelo formulario."""

        card = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("300.00"),
            balance=Decimal("120.00"),
        )

        response = self.client.post(
            reverse("cards:update", kwargs={"card_id": card.id}),
            data={
                "name": "Caju VA",
                "institution": self.institution.id,
                "card_type": Card.CardType.BENEFIT,
                "credit_limit": "",
                "statement_closing_day": "",
                "statement_due_day": "",
                "payment_account": "",
                "estimated_balance": "90.00",
                "is_active": "on",
            },
        )
        card.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(card.estimated_balance, Decimal("90.00"))
        self.assertEqual(card.balance, Decimal("90.00"))


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

    def test_statement_list_page_shows_computed_summary_values(self):
        """Lista de faturas deve mostrar valores calculados das compras vinculadas."""

        closing_date = timezone.localdate() + timedelta(days=5)
        due_date = closing_date + timedelta(days=7)
        statement = CardStatement.objects.create(
            card=self.card,
            year=closing_date.year,
            month=closing_date.month,
            closing_date=closing_date,
            due_date=due_date,
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=closing_date - timedelta(days=3),
        )

        response = self.client.get(reverse("cards:statements"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R$ 350,00")
        summary = response.context["statements"][0].summary
        self.assertEqual(summary["expected_amount"], Decimal("350.00"))
        self.assertEqual(summary["closed_amount"], Decimal("0.00"))
        self.assertEqual(summary["remaining_amount"], Decimal("350.00"))

    def test_statement_list_page_auto_closes_due_statement(self):
        """Listagem deve fechar automaticamente fatura com fechamento atingido."""

        closing_date = timezone.localdate() - timedelta(days=1)
        due_date = timezone.localdate() + timedelta(days=5)
        statement = CardStatement.objects.create(
            card=self.card,
            year=closing_date.year,
            month=closing_date.month,
            closing_date=closing_date,
            due_date=due_date,
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=closing_date,
        )

        response = self.client.get(reverse("cards:statements"))
        statement.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(statement.expected_amount, Decimal("350.00"))
        self.assertEqual(statement.closed_amount, Decimal("350.00"))
        self.assertEqual(statement.status, CardStatement.StatementStatus.PENDING)
        self.assertContains(response, "Pendente")

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
        self.assertContains(response, "Previsto")
        self.assertContains(response, "Fechado")
        self.assertContains(response, "Pago")
        self.assertContains(response, "Pendente")

    def test_statement_detail_page_shows_contextual_summary_values(self):
        """Deve exibir o resumo calculado com os valores corretos."""

        statement = self._create_statement(amount=Decimal("350.00"))
        statement.paid_amount = Decimal("125.00")
        statement.save(update_fields=["paid_amount"])

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R$ 350,00")
        self.assertContains(response, "R$ 125,00")
        self.assertContains(response, "R$ 225,00")

    def test_statement_detail_page_keeps_open_statement_closed_amount_empty(self):
        """Fatura aberta deve mostrar previsto e pendente sem valor fechado."""

        statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=5,
            closing_date="2026-05-20",
            due_date="2026-05-27",
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date="2026-05-08",
        )

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertEqual(response.context["statement_summary"]["expected_amount"], Decimal("350.00"))
        self.assertEqual(response.context["statement_summary"]["closed_amount"], Decimal("0.00"))
        self.assertEqual(response.context["statement_summary"]["remaining_amount"], Decimal("350.00"))

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

    def test_get_pay_statement_shows_confirmation(self):
        """Deve mostrar tela de confirmacao no GET."""

        statement = self._create_statement(amount=Decimal("350.00"))

        response = self.client.get(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id}),
            data={"amount": "350,00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/confirm_payment.html")
        self.assertContains(response, "Confirmar Pagamento")
        self.assertContains(response, "Saldo atual da conta")
        self.assertContains(response, "R$ 1.000,00")
        self.assertContains(response, "R$ 350,00")
        self.assertContains(response, "Saldo projetado após pagamento")
        self.assertContains(response, "R$ 650,00")

    def test_get_pay_statement_without_amount_uses_remaining_balance(self):
        """Deve usar o saldo restante se o valor nao for informado no GET."""

        statement = self._create_statement(amount=Decimal("350.00"))

        response = self.client.get(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R$ 350,00")

    def test_post_pay_statement_success_redirects_with_message(self):
        """Pagamento bem sucedido deve redirecionar com mensagem."""

        statement = self._create_statement(amount=Decimal("350.00"))

        response = self.client.post(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id}),
            data={"amount": "350,00"},
            follow=True
        )

        self.assertRedirects(
            response,
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )
        self.assertContains(response, "Fatura paga com sucesso.")

    def test_post_pay_statement_accepts_partial_payment_with_computed_remaining_amount(self):
        """Pagamento parcial deve validar contra o total calculado da fatura."""

        due_date = timezone.localdate() + timedelta(days=5)
        closing_date = due_date - timedelta(days=7)
        statement = CardStatement.objects.create(
            card=self.card,
            year=due_date.year,
            month=due_date.month,
            closing_date=closing_date,
            due_date=due_date,
            status=CardStatement.StatementStatus.PENDING,
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=closing_date,
        )

        response = self.client.post(
            reverse("cards:pay-statement", kwargs={"statement_id": statement.id}),
            data={"amount": "150,00"},
            follow=True,
        )
        statement.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id}),
        )
        self.assertContains(response, "Fatura paga com sucesso.")
        self.assertEqual(statement.paid_amount, Decimal("150.00"))
        self.assertEqual(statement.closed_amount, Decimal("350.00"))
        self.assertEqual(
            statement.status,
            CardStatement.StatementStatus.PARTIALLY_PAID,
        )

    def _create_statement(self, *, amount=Decimal("250.00")):
        """Cria uma fatura fechada com compra vinculada."""

        due_date = timezone.localdate() + timedelta(days=5)
        closing_date = due_date - timedelta(days=7)
        statement = CardStatement.objects.create(
            card=self.card,
            year=due_date.year,
            month=due_date.month,
            expected_amount=amount,
            closing_date=closing_date,
            due_date=due_date,
            payment_account=self.payment_account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=amount,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=statement,
            date=closing_date,
        )

        return close_statement(statement=statement)
