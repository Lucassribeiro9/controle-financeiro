"""Testes do detalhe dos cards do resumo financeiro da home."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from core.testing import AuthenticatedTestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from cards.models import Card
from core.selectors import get_operational_home_context, get_summary_card_detail
from institutions.models import Institution
from recurrences.models import Recurrence
from recurrences.services import generate_monthly_recurrences_forecasts
from transactions.models import Transaction, Transfer


class SummaryDetailFixtureMixin:
    """Monta um mes com lancamentos em todos os status e tipos do resumo."""

    today = date(2026, 5, 27)

    def create_fixture(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
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
            statement_due_day=10,
            payment_account=self.account,
        )

        self.salary = self.create_transaction(
            "Salario",
            "3000.00",
            Transaction.TransactionType.INCOME,
            Transaction.PaymentStatus.PAID,
        )
        self.market = self.create_transaction(
            "Mercado",
            "200.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.PAID,
        )
        self.card_purchase = self.create_transaction(
            "Compra no cartao",
            "150.00",
            Transaction.TransactionType.CARD_PURCHASE,
            Transaction.PaymentStatus.PAID,
            account=None,
            card=self.card,
        )
        self.benefit = self.create_transaction(
            "Vale refeicao",
            "80.00",
            Transaction.TransactionType.BENEFIT_PURCHASE,
            Transaction.PaymentStatus.PAID,
        )
        self.pending_income = self.create_transaction(
            "Freela a receber",
            "500.00",
            Transaction.TransactionType.INCOME,
            Transaction.PaymentStatus.PENDING,
        )
        self.partial_expense = self.create_transaction(
            "Aluguel parcial",
            "900.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.PARTIALLY_PAID,
        )
        self.late_expense = self.create_transaction(
            "Conta de luz",
            "120.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.LATE,
        )
        self.forecast_income = self.create_transaction(
            "Bonus previsto",
            "700.00",
            Transaction.TransactionType.INCOME,
            Transaction.PaymentStatus.FORECASTED,
        )
        self.forecast_expense = self.create_transaction(
            "Viagem prevista",
            "300.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.FORECASTED,
        )
        self.other_month = self.create_transaction(
            "Despesa de abril",
            "999.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.PAID,
            when=date(2026, 4, 30),
        )
        self.canceled = self.create_transaction(
            "Despesa cancelada",
            "888.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.CANCELED,
        )

        destination = FinancialAccount.objects.create(
            name="Reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("0.00"),
        )
        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("250.00"),
            from_account=self.account,
            destination_account=destination,
            date=date(2026, 5, 10),
        )

    def create_transaction(
        self,
        description,
        amount,
        transaction_type,
        status,
        *,
        account="default",
        card=None,
        when=date(2026, 5, 10),
    ):
        return Transaction.objects.create(
            description=description,
            amount=Decimal(amount),
            transaction_type=transaction_type,
            status=status,
            account=self.account if account == "default" else account,
            card=card,
            date=when,
        )

    def create_recurrences(self):
        Recurrence.objects.create(
            name="Internet residencial",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
        )
        Recurrence.objects.create(
            name="Aluguel recebido",
            expected_day=12,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.INCOME,
            expected_amount=Decimal("1500.00"),
            account=self.account,
        )
        generate_monthly_recurrences_forecasts(year=2026, month=5)


def _descriptions(section):
    return {transaction.description for transaction in section["transactions"]}


class SummaryCardDetailSelectorTests(SummaryDetailFixtureMixin, AuthenticatedTestCase):
    """Garante que o detalhe usa os mesmos criterios dos totais do card."""

    def setUp(self):
        self.create_fixture()

    def test_realized_lists_paid_income_and_all_expense_types(self):
        """Realizado deve separar receitas pagas de despesas, cartao e beneficio."""

        detail = get_summary_card_detail(card="realized", today=self.today)

        self.assertEqual(_descriptions(detail["income"]), {"Salario"})
        self.assertEqual(
            _descriptions(detail["expenses"]),
            {"Mercado", "Compra no cartao", "Vale refeicao"},
        )

    def test_pending_lists_pending_partially_paid_and_late(self):
        """Pendente deve incluir pendente, parcialmente pago e atrasado."""

        detail = get_summary_card_detail(card="pending", today=self.today)

        self.assertEqual(_descriptions(detail["income"]), {"Freela a receber"})
        self.assertEqual(
            _descriptions(detail["expenses"]),
            {"Aluguel parcial", "Conta de luz"},
        )

    def test_forecasted_lists_forecasted_transactions(self):
        """Previsto deve listar lancamentos com status previsto."""

        detail = get_summary_card_detail(card="forecasted", today=self.today)

        self.assertEqual(_descriptions(detail["income"]), {"Bonus previsto"})
        self.assertEqual(_descriptions(detail["expenses"]), {"Viagem prevista"})

    def test_forecasted_includes_recurring_forecasts_classified_by_recurrence(self):
        """Previsoes recorrentes entram como receita ou despesa conforme a recorrencia."""

        self.create_recurrences()

        detail = get_summary_card_detail(card="forecasted", today=self.today)

        self.assertIn("[REC] Aluguel recebido", _descriptions(detail["income"]))
        self.assertIn("[REC] Internet residencial", _descriptions(detail["expenses"]))

    def test_forecasted_excludes_recurring_forecasts_without_recurrence(self):
        """Previsao [REC] cuja recorrencia nao existe mais nao entra no detalhe."""

        self.create_transaction(
            "[REC] Recorrencia removida",
            "55.00",
            Transaction.TransactionType.FORECAST,
            Transaction.PaymentStatus.FORECASTED,
        )

        detail = get_summary_card_detail(card="forecasted", today=self.today)

        self.assertNotIn("[REC] Recorrencia removida", _descriptions(detail["income"]))
        self.assertNotIn("[REC] Recorrencia removida", _descriptions(detail["expenses"]))

    def test_forecasted_classifies_homonym_recurrences_by_linked_recurrence(self):
        """Recorrencias homonimas de tipos diferentes caem cada uma no seu lado."""

        for recurrence_type, amount in (
            (Recurrence.RecurrenceType.INCOME, "700.00"),
            (Recurrence.RecurrenceType.FIXED_BILL, "90.00"),
        ):
            recurrence = Recurrence.objects.create(
                name="Internet",
                expected_day=10,
                frequency=Recurrence.Frequency.MONTHLY,
                recurrence_type=recurrence_type,
                expected_amount=Decimal(amount),
                account=self.account,
            )
            Transaction.objects.create(
                description="[REC] Internet",
                amount=Decimal(amount),
                transaction_type=Transaction.TransactionType.FORECAST,
                status=Transaction.PaymentStatus.FORECASTED,
                account=self.account,
                date=date(2026, 5, 10),
                recurrence=recurrence,
            )

        detail = get_summary_card_detail(card="forecasted", today=self.today)

        self.assertEqual(
            [t.amount for t in detail["income"]["transactions"] if t.recurrence_id],
            [Decimal("700.00")],
        )
        self.assertEqual(
            [t.amount for t in detail["expenses"]["transactions"] if t.recurrence_id],
            [Decimal("90.00")],
        )

    def test_forecasted_keeps_recurring_forecast_after_recurrence_rename(self):
        """Renomear a recorrencia nao tira a previsao do detalhe."""

        self.create_recurrences()
        Recurrence.objects.filter(name="Aluguel recebido").update(name="Aluguel novo")

        detail = get_summary_card_detail(card="forecasted", today=self.today)

        self.assertIn("[REC] Aluguel recebido", _descriptions(detail["income"]))

    def test_forecasted_excludes_recurring_forecast_after_recurrence_deleted(self):
        """Apagar a recorrencia deixa a previsao sem vinculo, fora do detalhe."""

        self.create_recurrences()
        Recurrence.objects.filter(name="Aluguel recebido").delete()

        detail = get_summary_card_detail(card="forecasted", today=self.today)

        self.assertNotIn("[REC] Aluguel recebido", _descriptions(detail["income"]))

    def test_excludes_other_months_canceled_and_transfers(self):
        """Outros meses, cancelados e transferencias nao entram em nenhum card."""

        for card in ["realized", "pending", "forecasted"]:
            detail = get_summary_card_detail(card=card, today=self.today)
            listed = _descriptions(detail["income"]) | _descriptions(detail["expenses"])

            self.assertNotIn("Despesa de abril", listed)
            self.assertNotIn("Despesa cancelada", listed)

    def test_totals_match_home_summary_for_every_card(self):
        """Invariante: subtotais do detalhe sao iguais aos valores do card na home."""

        self.create_recurrences()
        summary = get_operational_home_context(today=self.today)["summary"]

        for card in ["realized", "pending", "forecasted"]:
            detail = get_summary_card_detail(card=card, today=self.today)

            self.assertEqual(detail["income"]["total"], summary[card]["income"], card)
            self.assertEqual(
                detail["expenses"]["total"], summary[card]["expenses"], card
            )
            self.assertEqual(detail["net"], summary[card]["net"], card)

    def test_returns_label_and_period(self):
        """O detalhe deve expor titulo do card e periodo usado."""

        detail = get_summary_card_detail(card="pending", today=self.today)

        self.assertEqual(detail["card"], "pending")
        self.assertEqual(detail["label"], "Pendente")
        self.assertEqual(detail["period"], {"year": 2026, "month": 5})

    def test_empty_month_returns_empty_sections_with_zero_totals(self):
        """Mes sem lancamentos deve retornar listas vazias e totais zerados."""

        detail = get_summary_card_detail(card="realized", today=date(2025, 1, 15))

        self.assertEqual(list(detail["income"]["transactions"]), [])
        self.assertEqual(list(detail["expenses"]["transactions"]), [])
        self.assertEqual(detail["income"]["total"], Decimal("0.00"))
        self.assertEqual(detail["net"], Decimal("0.00"))

    def test_unknown_card_raises_value_error(self):
        """Card desconhecido deve falhar explicitamente."""

        with self.assertRaises(ValueError):
            get_summary_card_detail(card="invalid", today=self.today)


class SummaryDetailViewTests(SummaryDetailFixtureMixin, AuthenticatedTestCase):
    """Garante o fluxo HTTP e o template do detalhe dos cards."""

    def setUp(self):
        self.create_fixture()
        patcher = patch("django.utils.timezone.localdate", return_value=self.today)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_detail_returns_success_for_each_card(self):
        """Cada card valido deve renderizar o template de detalhe."""

        for card in ["realized", "pending", "forecasted"]:
            response = self.client.get(reverse("core:summary_detail", args=[card]))

            self.assertEqual(response.status_code, 200, card)
            self.assertTemplateUsed(response, "core/summary_detail.html")
            self.assertTemplateUsed(response, "partials/transaction_table.html")

    def test_detail_returns_404_for_invalid_card(self):
        """Card fora do contrato deve retornar 404."""

        response = self.client.get(reverse("core:summary_detail", args=["invalid"]))

        self.assertEqual(response.status_code, 404)

    def test_detail_shows_income_and_expense_sections(self):
        """Receitas e despesas devem aparecer em secoes separadas."""

        Transaction.objects.all().delete()
        self.create_transaction(
            "Salario atual",
            "100.00",
            Transaction.TransactionType.INCOME,
            Transaction.PaymentStatus.PAID,
        )
        self.create_transaction(
            "Mercado atual",
            "40.00",
            Transaction.TransactionType.EXPENSE,
            Transaction.PaymentStatus.PAID,
        )

        response = self.client.get(reverse("core:summary_detail", args=["realized"]))

        self.assertContains(response, "Receitas")
        self.assertContains(response, "Despesas")
        self.assertContains(response, "Salario atual")
        self.assertContains(response, "Mercado atual")
        self.assertContains(response, "R$ 100,00")
        self.assertContains(response, "R$ 40,00")

    def test_detail_shows_empty_state_when_card_has_no_transactions(self):
        """Card sem lancamentos deve abrir o detalhe com empty state."""

        Transaction.objects.all().delete()

        response = self.client.get(reverse("core:summary_detail", args=["pending"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum lançamento")
        self.assertContains(response, reverse("transactions:create"))

    def test_detail_links_back_to_home(self):
        """O detalhe deve oferecer retorno para a home."""

        response = self.client.get(reverse("core:summary_detail", args=["realized"]))

        self.assertContains(response, reverse("core:home"))


class HomeSummaryCardTemplateTests(SummaryDetailFixtureMixin, AuthenticatedTestCase):
    """Garante que os cards da home sao links para o detalhe."""

    def test_home_cards_link_to_summary_detail(self):
        """Cada card do resumo deve ser um link para o detalhe correspondente."""

        response = self.client.get(reverse("core:home"))

        for card in ["realized", "pending", "forecasted"]:
            url = reverse("core:summary_detail", args=[card])
            self.assertContains(response, f'href="{url}"')

    def test_home_cards_show_click_indicator(self):
        """Os cards devem indicar visualmente que sao clicaveis."""

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "home-summary-card-link", count=3)
        self.assertContains(response, "Ver lançamentos", count=3)

    def test_home_cards_stay_clickable_when_month_is_empty(self):
        """Card zerado continua clicavel e a home mantem o empty state."""

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "home-summary-card-link", count=3)
        self.assertTrue(response.context["empty_states"]["summary"]["is_empty"])
