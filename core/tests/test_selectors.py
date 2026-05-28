"""Testes dos selectors da home operacional."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from core.selectors import get_operational_home_context
from goals.models import Goal, MonthlyGoal
from imports.models import ImportedTransaction
from insights.models import Insight
from institutions.models import Institution
from transactions.models import Transaction, Transfer


class OperationalHomeSelectorTests(TestCase):
    """Garante o contrato minimo do contexto da home operacional."""

    def setUp(self):
        self.today = date(2026, 5, 27)
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.destination_account = FinancialAccount.objects.create(
            name="Reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("500.00"),
        )

    def test_get_operational_home_context_returns_contract_with_empty_database(self):
        """Deve retornar todas as chaves esperadas sem dados financeiros."""

        context = get_operational_home_context(today=self.today)

        self.assertEqual(
            set(context.keys()),
            {"summary", "alerts", "pending_items", "quick_actions", "empty_states"},
        )
        self.assertEqual(context["summary"]["period"], {"year": 2026, "month": 5})
        self.assertEqual(context["summary"]["realized"]["income"], Decimal("0.00"))
        self.assertEqual(context["summary"]["realized"]["expenses"], Decimal("0.00"))
        self.assertEqual(context["summary"]["pending"]["income"], Decimal("0.00"))
        self.assertEqual(context["summary"]["forecasted"]["expenses"], Decimal("0.00"))
        self.assertEqual(context["summary"]["transfers"], Decimal("0.00"))
        self.assertEqual(context["alerts"], [])
        self.assertEqual(context["pending_items"], [])
        self.assertTrue(context["empty_states"]["summary"]["is_empty"])
        self.assertTrue(context["empty_states"]["alerts"]["is_empty"])
        self.assertTrue(context["empty_states"]["pending_items"]["is_empty"])

    def test_month_summary_separates_realized_pending_and_forecasted_values(self):
        """Deve separar realizados, pendentes e previstos no resumo mensal."""

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 5),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("450.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 6),
        )
        Transaction.objects.create(
            description="Internet",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.account,
            date=date(2026, 5, 10),
        )
        Transaction.objects.create(
            description="Assinatura prevista",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 5, 15),
        )
        Transaction.objects.create(
            description="Receita outro mes",
            amount=Decimal("9000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 6, 1),
        )

        summary = get_operational_home_context(today=self.today)["summary"]

        self.assertEqual(summary["realized"]["income"], Decimal("5000.00"))
        self.assertEqual(summary["realized"]["expenses"], Decimal("450.00"))
        self.assertEqual(summary["realized"]["net"], Decimal("4550.00"))
        self.assertEqual(summary["pending"]["expenses"], Decimal("120.00"))
        self.assertEqual(summary["forecasted"]["expenses"], Decimal("50.00"))

    def test_month_summary_keeps_transfers_out_of_income_and_expenses(self):
        """Transferencias nao devem virar receita ou despesa no resumo."""

        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        summary = get_operational_home_context(today=self.today)["summary"]

        self.assertEqual(summary["realized"]["income"], Decimal("0.00"))
        self.assertEqual(summary["realized"]["expenses"], Decimal("0.00"))
        self.assertEqual(summary["pending"]["income"], Decimal("0.00"))
        self.assertEqual(summary["pending"]["expenses"], Decimal("0.00"))
        self.assertEqual(summary["forecasted"]["income"], Decimal("0.00"))
        self.assertEqual(summary["forecasted"]["expenses"], Decimal("0.00"))
        self.assertEqual(summary["transfers"], Decimal("300.00"))

    def test_context_includes_existing_alerts_and_pending_items(self):
        """Deve usar dados existentes para alertas e pendencias acionaveis."""

        card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=10,
            payment_account=self.account,
        )
        CardStatement.objects.create(
            card=card,
            year=2026,
            month=5,
            closed_amount=Decimal("700.00"),
            expected_amount=Decimal("700.00"),
            due_date=date(2026, 6, 5),
            closing_date=date(2026, 5, 20),
            status=CardStatement.StatementStatus.OPEN,
            payment_account=self.account,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado",
            normalized_description="mercado",
            amount=Decimal("100.00"),
            date=date(2026, 5, 20),
            status=ImportedTransaction.Status.PENDING,
        )
        Insight.objects.create(
            title="Assinatura recorrente",
            message="Possivel assinatura",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            status=Insight.Status.PENDING,
        )
        goal = Goal.objects.create(
            name="Mercado",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("1000.00"),
            start_date=date(2026, 5, 1),
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("850.00"),
        )

        context = get_operational_home_context(today=self.today)

        self.assertEqual(
            [alert["type"] for alert in context["alerts"]],
            ["card_statement", "imports", "goal"],
        )
        self.assertEqual(
            [item["type"] for item in context["pending_items"]],
            ["imports", "insights"],
        )
        self.assertFalse(context["empty_states"]["alerts"]["is_empty"])
        self.assertFalse(context["empty_states"]["pending_items"]["is_empty"])

    def test_pending_items_include_forecasted_transactions(self):
        """Deve listar recorrencias previstas como pendencia acionavel."""

        Transaction.objects.create(
            description="Assinatura prevista",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 5, 15),
        )

        pending_items = get_operational_home_context(today=self.today)["pending_items"]

        self.assertEqual(
            pending_items,
            [
                {
                    "type": "recurrences",
                    "title": "Revisar recorrencias previstas",
                    "count": 1,
                    "url": reverse("recurrences:forecasts-page", args=[2026, 5]),
                }
            ],
        )

    def test_quick_actions_point_to_existing_flows(self):
        """Atalhos fixos devem apontar para rotas existentes."""

        quick_actions = get_operational_home_context(today=self.today)["quick_actions"]

        self.assertEqual(
            quick_actions,
            [
                {
                    "title": "Novo lancamento",
                    "url": reverse("transactions:create"),
                },
                {
                    "title": "Nova transferencia",
                    "url": reverse("transactions:transfer-create"),
                },
                {
                    "title": "Revisar importacoes",
                    "url": reverse("imports:review-page"),
                },
                {
                    "title": "Ver faturas",
                    "url": reverse("cards:statements"),
                },
            ],
        )
