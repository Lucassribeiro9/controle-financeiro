"""Testes das views do app core."""

from datetime import date
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import FinancialAccount
from cards.models import Card
from cards.models import CardStatement
from goals.models import Goal
from goals.models import MonthlyGoal
from imports.models import ImportedTransaction
from insights.models import Insight
from institutions.models import Institution
from transactions.models import Transaction


class HomeViewTests(TestCase):
    """Garante que a home consome o contexto operacional."""

    def test_home_renders_with_empty_database(self):
        """A home deve renderizar sem excecao quando nao ha dados financeiros."""

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_home_context_includes_operational_contract(self):
        """A view deve expor as chaves principais retornadas pelo selector."""

        response = self.client.get(reverse("core:home"))

        for key in [
            "summary",
            "alerts",
            "pending_items",
            "quick_actions",
            "empty_states",
        ]:
            self.assertIn(key, response.context)

        self.assertEqual(
            response.context["summary"]["realized"]["income"],
            Decimal("0.00"),
        )
        self.assertEqual(response.context["alerts"], [])
        self.assertEqual(response.context["pending_items"], [])
        self.assertTrue(response.context["empty_states"]["summary"]["is_empty"])

    def test_home_displays_empty_month_summary(self):
        """Banco vazio deve exibir resumo zerado de forma compreensivel."""

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Resumo financeiro do mês")
        self.assertContains(response, "Sem lançamentos")
        self.assertContains(response, "Nenhum lancamento neste mes")
        self.assertContains(response, "R$ 0,00")

    def test_home_displays_month_summary_with_real_transactions(self):
        """A home deve separar valores realizados, pendentes e previstos."""

        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        period = self.client.get(reverse("core:home")).context["summary"]["period"]
        year = period["year"]
        month = period["month"]

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            date=date(year, month, 5),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("450.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            date=date(year, month, 6),
        )
        Transaction.objects.create(
            description="Internet",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=account,
            date=date(year, month, 10),
        )
        Transaction.objects.create(
            description="Assinatura prevista",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.FORECASTED,
            account=account,
            date=date(year, month, 15),
        )

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Realizado")
        self.assertContains(response, "Pendente")
        self.assertContains(response, "Previsto")
        self.assertContains(response, "R$ 5.000,00")
        self.assertContains(response, "R$ 450,00")
        self.assertContains(response, "R$ 4.550,00")
        self.assertContains(response, "-R$ 120,00")
        self.assertContains(response, "-R$ 50,00")

    def test_home_displays_empty_alert_state(self):
        """Sem alertas, a home deve mostrar um estado vazio acionavel."""

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Alertas prioritários")
        self.assertContains(response, "Nenhum alerta prioritario")
        self.assertContains(response, "Ver dashboard mensal")
        self.assertContains(response, 'href="/reports/month/"', html=False)

    def test_home_displays_priority_alerts_with_links(self):
        """Alertas existentes devem aparecer com links para os fluxos responsaveis."""

        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        card = Card.objects.create(
            name="Inter Gold",
            institution=institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=10,
            payment_account=account,
        )
        statement = CardStatement.objects.create(
            card=card,
            year=2026,
            month=5,
            closed_amount=Decimal("700.00"),
            expected_amount=Decimal("700.00"),
            due_date=timezone.localdate() + timedelta(days=5),
            closing_date=timezone.localdate(),
            status=CardStatement.StatementStatus.OPEN,
            payment_account=account,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado",
            normalized_description="mercado",
            amount=Decimal("100.00"),
            date=timezone.localdate(),
            status=ImportedTransaction.Status.PENDING,
        )
        period = self.client.get(reverse("core:home")).context["summary"]["period"]
        goal = Goal.objects.create(
            name="Mercado",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("1000.00"),
            start_date=date(period["year"], period["month"], 1),
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=period["year"],
            month=period["month"],
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("850.00"),
        )

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Fatura Inter Gold")
        self.assertContains(response, "Prioridade alta")
        self.assertContains(response, "R$ 700,00")
        self.assertContains(
            response,
            reverse("cards:statement-detail", args=[statement.id]),
        )
        self.assertContains(response, "Importacoes pendentes")
        self.assertContains(response, "1 lancamento(s) aguardando revisao")
        self.assertContains(response, reverse("imports:review-page"))
        self.assertContains(response, "Mercado")
        self.assertContains(response, "Meta mensal em risco")
        self.assertContains(response, "R$ 850,00 de R$ 1.000,00")
        self.assertContains(response, reverse("goals:monthly-goals"))

    def test_home_displays_empty_pending_items_state(self):
        """Sem pendencias, a home deve mostrar estado vazio acionavel."""

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Pendências acionáveis")
        self.assertContains(response, "Nenhuma pendencia operacional")
        self.assertContains(response, "Ver recorrencias")
        self.assertContains(
            response,
            reverse("recurrences:forecasts-filter-page"),
        )

    def test_home_displays_actionable_pending_items_with_links(self):
        """Pendencias existentes devem apontar para os fluxos completos."""

        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado",
            normalized_description="mercado",
            amount=Decimal("100.00"),
            date=timezone.localdate(),
            status=ImportedTransaction.Status.PENDING,
        )
        Insight.objects.create(
            title="Assinatura recorrente",
            message="Possivel assinatura recorrente",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            status=Insight.Status.PENDING,
        )
        period = self.client.get(reverse("core:home")).context["summary"]["period"]
        Transaction.objects.create(
            description="Aluguel previsto",
            amount=Decimal("1500.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.FORECASTED,
            account=account,
            date=date(period["year"], period["month"], 20),
        )

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Revisar importacoes")
        self.assertContains(response, reverse("imports:review-page"))
        self.assertContains(response, "Revisar insights")
        self.assertContains(response, reverse("insights:page"))
        self.assertContains(response, "Revisar recorrencias previstas")
        self.assertContains(
            response,
            reverse(
                "recurrences:forecasts-page",
                args=[period["year"], period["month"]],
            ),
        )
        self.assertContains(response, "Importações")
        self.assertContains(response, "Insights")
        self.assertContains(response, "Recorrências")

        self.assertEqual(
            ImportedTransaction.objects.filter(
                status=ImportedTransaction.Status.PENDING,
            ).count(),
            1,
        )
        self.assertEqual(
            Insight.objects.filter(status=Insight.Status.PENDING).count(),
            1,
        )
        self.assertEqual(
            Transaction.objects.filter(
                status=Transaction.PaymentStatus.FORECASTED,
            ).count(),
            1,
        )
