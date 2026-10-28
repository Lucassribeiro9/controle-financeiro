"""Testes da rotina diaria de manutencao (ADR-013)."""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from categories.models import Category
from core.demo_data import build_realistic_month
from core.maintenance import run_daily_maintenance
from goals.models import Goal, MonthlyGoal
from insights.models import Insight
from institutions.models import Institution
from recurrences.models import Recurrence
from transactions.models import Transaction

TODAY = date(2026, 6, 15)


class DailyMaintenanceTests(TestCase):
    """Garante efeitos, idempotencia e isolamento dos passos."""

    def setUp(self):
        institution = Institution.objects.create(name="Banco Teste", code="999")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.recurrence = Recurrence.objects.create(
            name="Internet",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
            requires_confirmation=True,
            is_active=True,
        )
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=5,
            statement_due_day=12,
            payment_account=self.account,
        )
        self.open_statement = CardStatement.objects.create(
            card=self.card,
            year=2026,
            month=6,
            closing_date=date(2026, 6, 5),
            due_date=date(2026, 6, 12),
            payment_account=self.account,
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            statement=self.open_statement,
            date=date(2026, 6, 3),
        )
        self.category = Category.objects.create(name="Delivery")
        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            category=self.category,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 6, 1),
        )
        self.monthly_goal = MonthlyGoal.objects.create(
            goal=goal, year=2026, month=6, target_amount=Decimal("300.00")
        )
        Transaction.objects.create(
            description="Pizza",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            category=self.category,
            date=date(2026, 6, 10),
        )

    def test_runs_all_steps_in_order(self):
        report = run_daily_maintenance(today=TODAY)

        self.assertEqual(
            [step.name for step in report.steps],
            ["previsoes", "faturas_fechadas", "faturas_atrasadas", "metas", "insights"],
        )
        self.assertTrue(report.ok)

    def test_generates_forecast_for_current_month_only(self):
        run_daily_maintenance(today=TODAY)

        forecasts = Transaction.objects.filter(recurrence=self.recurrence)
        self.assertEqual([t.date for t in forecasts], [date(2026, 6, 10)])

    def test_closes_due_statement_then_marks_it_late(self):
        run_daily_maintenance(today=TODAY)

        self.open_statement.refresh_from_db()
        self.assertEqual(self.open_statement.status, CardStatement.StatementStatus.LATE)
        self.assertEqual(self.open_statement.closed_amount, Decimal("200.00"))

    def test_refreshes_current_month_goals(self):
        run_daily_maintenance(today=TODAY)

        self.monthly_goal.refresh_from_db()
        self.assertEqual(self.monthly_goal.current_amount, Decimal("250.00"))
        self.assertEqual(self.monthly_goal.status, MonthlyGoal.Status.AT_RISK)

    def test_generates_insights_for_previous_month(self):
        build_realistic_month(year=2026, month=5)

        report = run_daily_maintenance(today=TODAY)

        self.assertGreater(Insight.objects.count(), 0)
        insights_step = report.steps[-1]
        self.assertEqual(insights_step.count, Insight.objects.count())

    def test_previous_month_wraps_year(self):
        with mock.patch("core.maintenance.generate_monthly_insights", return_value=[]) as gen:
            run_daily_maintenance(today=date(2026, 1, 3))

        gen.assert_called_once_with(year=2025, month=12)

    def test_running_twice_same_day_does_not_duplicate(self):
        build_realistic_month(year=2026, month=5)

        run_daily_maintenance(today=TODAY)
        snapshot = (
            Transaction.objects.count(),
            Insight.objects.count(),
            MonthlyGoal.objects.count(),
            CardStatement.objects.values_list("status", "closed_amount").get(
                pk=self.open_statement.pk
            ),
        )
        second = run_daily_maintenance(today=TODAY)

        self.assertEqual(
            snapshot,
            (
                Transaction.objects.count(),
                Insight.objects.count(),
                MonthlyGoal.objects.count(),
                CardStatement.objects.values_list("status", "closed_amount").get(
                    pk=self.open_statement.pk
                ),
            ),
        )
        counts = {step.name: step.count for step in second.steps}
        self.assertEqual(counts["previsoes"], 0)
        self.assertEqual(counts["faturas_fechadas"], 0)
        self.assertEqual(counts["faturas_atrasadas"], 0)
        self.assertEqual(counts["insights"], 0)

    def test_failing_step_does_not_stop_others_and_rolls_back(self):
        def broken(*, year, month):
            Transaction.objects.create(
                description="lixo",
                amount=Decimal("1.00"),
                transaction_type=Transaction.TransactionType.EXPENSE,
                status=Transaction.PaymentStatus.PAID,
                account=self.account,
                date=TODAY,
            )
            raise RuntimeError("falha simulada")

        with mock.patch("core.maintenance.generate_monthly_recurrences_forecasts", broken):
            report = run_daily_maintenance(today=TODAY)

        self.assertFalse(report.ok)
        self.assertEqual(report.steps[0].error, "falha simulada")
        self.assertFalse(Transaction.objects.filter(description="lixo").exists())
        self.open_statement.refresh_from_db()
        self.assertEqual(self.open_statement.status, CardStatement.StatementStatus.LATE)


class DailyMaintenanceCommandTests(TestCase):
    """Garante saida e codigo de erro do comando."""

    def test_prints_count_per_step(self):
        out = StringIO()
        call_command("daily_maintenance", stdout=out)

        text = out.getvalue()
        for name in ["previsoes", "faturas_fechadas", "faturas_atrasadas", "metas", "insights"]:
            self.assertIn(name, text)

    def test_raises_command_error_when_a_step_fails(self):
        out = StringIO()
        with mock.patch(
            "core.maintenance.refresh_monthly_goals", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(CommandError):
                call_command("daily_maintenance", stdout=out, stderr=StringIO())

        self.assertIn("metas", out.getvalue())
