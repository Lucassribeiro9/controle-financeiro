"""Tests das views do app cards."""

import re
from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal

from core.testing import AuthenticatedTestCase
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.services import close_statement
from cards.selectors import get_card_limits
from institutions.models import Institution
from transactions.models import Transaction


# Classes do antigo app.css que as telas de cartoes nao podem mais usar (FIN-52, spec 017).
LEGACY_CLASSES = {
    "panel", "page-header", "page-section", "button", "button-secondary", "data-table",
    "table-responsive", "metric-card", "detail-list", "summary-grid", "card-title-row",
    "form-grid", "form-field", "field-error", "action-row", "app-message", "inline-form",
    "limit-bar", "limit-bar-fill", "limit-bar-over", "cell-primary", "cell-amount",
    "cell-count", "cell-date", "cell-status", "cell-period", "muted", "sr-only",
}


def used_classes(response):
    """Conjunto de classes CSS usadas no HTML da resposta."""

    html = response.content.decode()
    return {
        name
        for attr in re.findall(r'class="([^"]*)"', html)
        for name in attr.split()
    }


class NewVisualMixin:
    """Contrato visual das telas de cartoes: casca, CSS da pagina e sem classes legadas."""

    def assertNewVisual(self, response, *, shell="nav"):
        self.assertContains(response, "css/pages/cards.css")
        self.assertContains(response, f'class="shell-{shell}"', html=False)
        self.assertEqual(used_classes(response) & LEGACY_CLASSES, set())
        self.assertFalse(
            {name for name in used_classes(response) if name.startswith("cards-")}
            - self.local_classes()
        )

    @staticmethod
    def local_classes():
        css = (settings.BASE_DIR / "static/css/pages/cards.css").read_text()
        return set(re.findall(r"\.(cards-[\w-]+)", css))


class CardViewTests(NewVisualMixin, AuthenticatedTestCase):
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
        self.assertContains(response, 'class="progress"', html=False)
        self.assertContains(response, 'role="progressbar"', html=False)
        self.assertContains(response, 'aria-valuenow="7"', html=False)
        self.assertNewVisual(response)

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
        self.assertContains(response, 'class="progress progress--over"', html=False)
        self.assertNewVisual(response)

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
        self.assertNotContains(response, 'role="progressbar"', html=False)
        self.assertNewVisual(response)

    def test_card_empty_states_use_new_visual(self):
        """Sem cartoes, a lista mostra o estado vazio do design system."""

        response = self.client.get(reverse("cards:list"))

        self.assertContains(response, "Nenhum cartão cadastrado.")
        self.assertContains(response, 'class="empty"', html=False)
        self.assertNewVisual(response)

    def test_card_update_page_uses_task_shell(self):
        """Edicao de cartao usa a casca de tarefa e o link de cancelar."""

        card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
        )

        response = self.client.get(reverse("cards:update", kwargs={"card_id": card.id}))

        self.assertEqual(response.status_code, 200)
        self.assertNewVisual(response, shell="task")
        self.assertContains(response, "Editar cartão")
        self.assertContains(response, 'class="field"', html=False)
        self.assertContains(response, reverse("cards:list"))

    def test_card_create_page_returns_form(self):
        """Deve renderizar formulario de criacao de cartao."""

        response = self.client.get(reverse("cards:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/form.html")
        self.assertContains(response, "Novo cartão")
        self.assertNewVisual(response, shell="task")
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


    def test_post_create_transport_and_prepaid_cards_copy_balance(self):
        """Transporte e pre-pago guardam o saldo informado em balance."""

        for card_type in (Card.CardType.TRANSPORT, Card.CardType.PREPAID):
            with self.subTest(card_type=card_type):
                response = self.client.post(
                    reverse("cards:create"),
                    data={
                        "name": f"Cartao {card_type}",
                        "institution": self.institution.id,
                        "card_type": card_type,
                        "credit_limit": "",
                        "statement_closing_day": "",
                        "statement_due_day": "",
                        "payment_account": "",
                        "estimated_balance": "80,50",
                        "is_active": "on",
                    },
                )
                card = Card.objects.get(name=f"Cartao {card_type}")

                self.assertEqual(response.status_code, 302)
                self.assertEqual(card.balance, Decimal("80.50"))

    def test_edit_form_shows_own_balance_for_transport_card(self):
        """Edicao de cartao de transporte abre com o saldo atual."""

        card = Card.objects.create(
            name="VT",
            institution=self.institution,
            card_type=Card.CardType.TRANSPORT,
            balance=Decimal("42.00"),
        )

        response = self.client.get(reverse("cards:update", kwargs={"card_id": card.id}))

        self.assertEqual(
            response.context["form"].fields["estimated_balance"].initial,
            Decimal("42.00"),
        )

    def test_list_shows_balance_for_transport_and_prepaid_cards(self):
        """A lista mostra o saldo proprio do grupo de saldo."""

        Card.objects.create(
            name="VT",
            institution=self.institution,
            card_type=Card.CardType.TRANSPORT,
            balance=Decimal("42.00"),
            estimated_balance=Decimal("999.00"),
        )

        response = self.client.get(reverse("cards:list"))

        self.assertContains(response, "42,00")
        self.assertNotContains(response, "999,00")


class StatementViewTests(NewVisualMixin, AuthenticatedTestCase):
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
        self.assertContains(response, 'class="status status--warning"', html=False)
        self.assertNewVisual(response)

    def test_statement_list_page_shows_progress_against_card_limit(self):
        """Cada fatura mostra o quanto ela pesa no limite do cartao."""

        self._create_statement(amount=Decimal("1250.00"))

        response = self.client.get(reverse("cards:statements"))

        self.assertContains(response, 'class="progress"', html=False)
        self.assertContains(response, 'aria-valuenow="25"', html=False)
        self.assertContains(response, "25% do limite")

    def test_statement_list_page_without_credit_limit_has_no_progress(self):
        """Sem limite cadastrado nao ha barra de progresso."""

        self.card.credit_limit = None
        self.card.save(update_fields=["credit_limit"])
        self._create_statement()

        response = self.client.get(reverse("cards:statements"))

        self.assertNotContains(response, 'role="progressbar"', html=False)
        self.assertNewVisual(response)

    def test_statement_list_page_empty_state(self):
        """Sem faturas, mostra o estado vazio."""

        response = self.client.get(reverse("cards:statements"))

        self.assertContains(response, "Nenhuma fatura encontrada.")
        self.assertContains(response, 'class="empty"', html=False)
        self.assertNewVisual(response)

    def test_statement_detail_empty_transactions_state(self):
        """Fatura sem transacoes mostra o estado vazio no visual novo."""

        statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=5,
            closing_date="2026-05-20",
            due_date="2026-05-27",
        )

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertContains(response, "Nenhuma transação vinculada a esta fatura.")
        self.assertContains(response, 'class="empty"', html=False)
        self.assertNewVisual(response)

    def test_statement_detail_shows_statement_payment_as_credit(self):
        """Pagamento vinculado e credito da fatura: sinal +, icone e classe de credito."""

        statement = self._create_statement(amount=Decimal("250.00"))
        Transaction.objects.create(
            description="Pagamento da fatura",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            status=Transaction.PaymentStatus.PAID,
            card=self.card,
            statement=statement,
            date=timezone.localdate(),
        )

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertContains(response, '<span class="cards-tx__amount cards-tx__amount--in">+ R$ 100,00</span>', html=False)
        self.assertContains(response, 'class="cards-tx__icon cards-tx__icon--in"', html=False)
        self.assertContains(response, '<span class="cards-tx__amount">− R$ 250,00</span>', html=False)
        self.assertNewVisual(response)

    def test_statement_detail_shows_limit_progress_and_back_link(self):
        """Detalhe mostra o valor em destaque, o progresso e o link de voltar."""

        statement = self._create_statement(amount=Decimal("1250.00"))

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertContains(response, "25% do limite de R$ 5.000,00")
        self.assertContains(response, 'class="progress"', html=False)
        self.assertContains(response, "Voltar para faturas")
        self.assertContains(response, reverse("cards:statements"))
        self.assertContains(response, "R$ 1.250,00")

    def test_statement_detail_progress_goes_over_limit(self):
        """Fatura acima do limite usa a variante de excesso."""

        statement = self._create_statement(amount=Decimal("6000.00"))

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertContains(response, 'class="progress progress--over"', html=False)

    def test_statement_detail_keeps_post_close_and_get_pay_forms(self):
        """Fechar continua POST com CSRF e pagar continua GET com campo opcional."""

        statement = self._create_statement()
        statement_url = reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        pay_url = reverse("cards:pay-statement", kwargs={"statement_id": statement.id})

        response = self.client.get(statement_url)

        self.assertContains(response, 'name="csrfmiddlewaretoken"', html=False)
        self.assertContains(response, f'method="post" action="{statement_url}"', html=False)
        self.assertContains(response, f'method="get" action="{pay_url}"', html=False)
        self.assertContains(response, 'name="amount"', html=False)

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

    def test_statement_list_page_does_not_close_due_statement(self):
        """GET da listagem nao grava: fatura com fechamento atingido segue aberta (ADR-012)."""

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
        before = CardStatement.objects.values().get(pk=statement.pk)

        response = self.client.get(reverse("cards:statements"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CardStatement.objects.values().get(pk=statement.pk), before)
        statement.refresh_from_db()
        self.assertEqual(statement.status, CardStatement.StatementStatus.OPEN)
        self.assertContains(response, "Aberta")

    def test_statement_pages_do_not_mark_overdue_statement_as_late(self):
        """GET de lista e detalhe nao marca atraso; quem faz isso e a rotina diaria."""

        closing_date = timezone.localdate() - timedelta(days=20)
        statement = CardStatement.objects.create(
            card=self.card,
            year=closing_date.year,
            month=closing_date.month,
            closing_date=closing_date,
            due_date=timezone.localdate() - timedelta(days=5),
            closed_amount=Decimal("100.00"),
            expected_amount=Decimal("100.00"),
            status=CardStatement.StatementStatus.PENDING,
            payment_account=self.payment_account,
        )
        before = CardStatement.objects.values().get(pk=statement.pk)

        list_response = self.client.get(reverse("cards:statements"))
        detail_response = self.client.get(
            reverse("cards:statement-detail", args=[statement.pk])
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(CardStatement.objects.values().get(pk=statement.pk), before)

    def test_statement_detail_page_returns_success(self):
        """Deve renderizar detalhe da fatura."""

        statement = self._create_statement()

        response = self.client.get(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cards/statement_detail.html")
        self.assertContains(response, self.card.name)
        self.assertNewVisual(response)
        self.assertContains(response, "Pagar fatura")
        self.assertContains(response, "Fechar fatura")
        self.assertContains(response, "Transações vinculadas")
        self.assertContains(response, "Mercado")
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
        self.assertNewVisual(response, shell="task")
        self.assertContains(response, 'name="amount" value="350.00"', html=False)

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

    def test_close_canceled_statement_keeps_readable_message(self):
        statement = self._create_statement()
        statement.status = CardStatement.StatementStatus.CANCELED
        statement.save(update_fields=["status"])

        response = self.client.post(
            reverse("cards:statement-detail", kwargs={"statement_id": statement.id}),
            follow=True,
        )

        messages = [str(m) for m in response.context["messages"]]
        self.assertEqual(messages, ["Fatura cancelada nao pode ser fechada."])
