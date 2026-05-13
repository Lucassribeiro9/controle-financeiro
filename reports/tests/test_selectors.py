"""Tests dos seletores do app reports."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from institutions.models import Institution
from reports.selectors import (
    get_account_net_worth,
    get_card_statements,
    get_category_expense_breakdown,
    get_goal_summary,
    get_monthly_dashboard,
    get_monthly_expense_total,
    get_monthly_income_total,
)
from transactions.models import Transaction, Transfer


class ReportSelectorTests(TestCase):
    """Garante as consultas principais para dashboards e relatorios."""

    def setUp(self):
        """Cria dados base para cenarios de relatorio."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.savings_account = FinancialAccount.objects.create(
            name="Poupanca",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        self.usd_account = FinancialAccount.objects.create(
            name="Conta global",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.GLOBAL,
            currency=FinancialAccount.Currency.USD,
            balance=Decimal("100.00"),
        )
        self.inactive_account = FinancialAccount.objects.create(
            name="Conta encerrada",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("999.00"),
            is_active=False,
        )
        self.food_category = Category.objects.create(name="Alimentacao")
        self.transport_category = Category.objects.create(name="Transporte")

    def test_monthly_income_total_sums_income_for_period(self):
        """Deve somar receitas do mes informado."""

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 5),
        )
        Transaction.objects.create(
            description="Receita de outro mes",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 6, 5),
        )

        total = get_monthly_income_total(year=2026, month=5)

        self.assertEqual(total, Decimal("5000.00"))

    def test_monthly_expense_total_sums_expenses_for_period(self):
        """Deve somar despesas do mes informado."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.food_category,
            date=date(2026, 5, 10),
        )
        Transaction.objects.create(
            description="Onibus",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.account,
            category=self.transport_category,
            date=date(2026, 5, 11),
        )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("300.00"))

    def test_monthly_totals_ignore_forecasted_ignored_and_canceled(self):
        """Nao deve somar transacoes previstas, ignoradas ou canceladas."""

        for status in (
            Transaction.PaymentStatus.FORECASTED,
            Transaction.PaymentStatus.IGNORED,
            Transaction.PaymentStatus.CANCELED,
        ):
            Transaction.objects.create(
                description=f"Despesa {status}",
                amount=Decimal("100.00"),
                transaction_type=Transaction.TransactionType.EXPENSE,
                status=status,
                account=self.account,
                category=self.food_category,
                date=date(2026, 5, 10),
            )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("0.00"))

    def test_category_expense_breakdown_groups_expenses_by_category(self):
        """Deve agrupar despesas por categoria e ordenar por maior valor."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.food_category,
            date=date(2026, 5, 10),
        )
        Transaction.objects.create(
            description="Restaurante",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.food_category,
            date=date(2026, 5, 11),
        )
        Transaction.objects.create(
            description="Onibus",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.transport_category,
            date=date(2026, 5, 12),
        )

        breakdown = get_category_expense_breakdown(year=2026, month=5)

        self.assertEqual(breakdown[0]["category_id"], self.food_category.id)
        self.assertEqual(breakdown[0]["category__name"], "Alimentacao")
        self.assertEqual(breakdown[0]["total_amount"], Decimal("300.00"))
        self.assertEqual(breakdown[1]["category_id"], self.transport_category.id)
        self.assertEqual(breakdown[1]["total_amount"], Decimal("50.00"))

    def test_account_net_worth_groups_active_accounts_by_currency(self):
        """Deve somar patrimonio por moeda considerando apenas contas ativas."""

        net_worth = list(get_account_net_worth())

        self.assertEqual(
            net_worth,
            [
                {"currency": FinancialAccount.Currency.BRL, "total": Decimal("1500.00")},
                {"currency": FinancialAccount.Currency.USD, "total": Decimal("100.00")},
            ],
        )

    def test_card_statements_returns_statements_for_period(self):
        """Deve listar faturas do mes informado."""

        card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )
        statement = CardStatement.objects.create(
            card=card,
            year=2026,
            month=5,
            closed_amount=Decimal("1200.00"),
            paid_amount=Decimal("400.00"),
            closing_date=date(2026, 5, 20),
            due_date=date(2026, 5, 27),
            status=CardStatement.StatementStatus.PARTIALLY_PAID,
            payment_account=self.account,
        )
        CardStatement.objects.create(
            card=card,
            year=2026,
            month=6,
            closing_date=date(2026, 6, 20),
            due_date=date(2026, 6, 27),
            payment_account=self.account,
        )

        statements = list(get_card_statements(year=2026, month=5))

        self.assertEqual(statements, [statement])
        self.assertEqual(statements[0].card, card)

    def test_goal_summary_returns_monthly_goals_for_period(self):
        """Deve listar metas mensais do periodo informado."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("10000.00"),
            start_date=date(2026, 5, 1),
        )
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("400.00"),
            current_amount=Decimal("250.00"),
            status=MonthlyGoal.Status.ON_TRACK,
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=6,
            target_amount=Decimal("400.00"),
        )

        goals = list(get_goal_summary(year=2026, month=5))

        self.assertEqual(goals, [monthly_goal])
        self.assertEqual(goals[0].goal, goal)

    def test_monthly_dashboard_returns_expected_payload(self):
        """Deve montar payload consolidado do painel mensal."""

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
            amount=Decimal("300.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.food_category,
            date=date(2026, 5, 10),
        )
        Transfer.objects.create(
            description="Aporte",
            amount=Decimal("100.00"),
            from_account=self.account,
            destination_account=self.savings_account,
            date=date(2026, 5, 15),
        )

        dashboard = get_monthly_dashboard(year=2026, month=5)

        self.assertEqual(dashboard["year"], 2026)
        self.assertEqual(dashboard["month"], 5)
        self.assertEqual(dashboard["income_total"], Decimal("5000.00"))
        self.assertEqual(dashboard["expense_total"], Decimal("300.00"))
        self.assertEqual(dashboard["monthly_balance"], Decimal("4700.00"))
        self.assertEqual(dashboard["category_expenses"][0]["total_amount"], Decimal("300.00"))
