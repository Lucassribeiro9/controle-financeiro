"""Tests do command seed_demo_data e do modulo core.demo_data."""

from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.test import TestCase, override_settings

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from insights.models import Insight
from installments.models import InstallmentPlan
from institutions.models import Institution
from recurrences.models import Recurrence
from transactions.models import Transaction, Transfer

MODELS = (
    Institution,
    FinancialAccount,
    Card,
    CardStatement,
    Category,
    Transaction,
    Transfer,
    InstallmentPlan,
    Recurrence,
    Goal,
    MonthlyGoal,
    Insight,
)


def counts():
    return {model.__name__: model.objects.count() for model in MODELS}


def balances():
    return {
        account.name: account.balance
        for account in FinancialAccount.objects.order_by("name")
    }


def run(*args):
    out = StringIO()
    call_command("seed_demo_data", *args, stdout=out)
    return out.getvalue()


@override_settings(DEBUG=True)
class SeedDemoDataCommandTests(TestCase):
    def test_creates_expected_counts_per_model(self):
        run("--reset")

        result = counts()
        self.assertEqual(result["Institution"], 1)
        self.assertEqual(result["FinancialAccount"], 3)
        self.assertEqual(result["Card"], 1)
        self.assertEqual(result["CardStatement"], 6)
        self.assertEqual(result["Category"], 8)
        self.assertEqual(result["Transfer"], 3)
        self.assertEqual(result["InstallmentPlan"], 1)
        self.assertEqual(result["Recurrence"], 3)
        self.assertEqual(result["Goal"], 5)
        self.assertEqual(result["MonthlyGoal"], 15)
        self.assertEqual(result["Transaction"], 47)
        self.assertGreater(result["Insight"], 0)

    def test_covers_statuses_and_types_for_screens(self):
        run("--reset")

        statuses = set(Transaction.objects.values_list("status", flat=True))
        self.assertTrue({"paid", "pending", "forecasted"} <= statuses)
        types = set(Transaction.objects.values_list("transaction_type", flat=True))
        self.assertTrue(
            {"income", "expense", "card_purchase", "forecast", "statement_payment"}
            <= types
        )
        self.assertEqual(
            Transaction.objects.filter(installment_plan__isnull=False).count(), 6
        )
        self.assertTrue(
            Insight.objects.filter(status=Insight.Status.PENDING).exists()
        )
        self.assertEqual(
            set(
                Goal.objects.filter(goal_type=Goal.GoalType.REDUCTION).values_list(
                    "category_id", flat=True
                )
            ).__len__(),
            3,
        )
        paid = CardStatement.objects.filter(status=CardStatement.StatementStatus.PAID)
        self.assertEqual(paid.count(), 1)

    def test_reset_twice_gives_same_result(self):
        run("--reset")
        first = (counts(), balances())

        run("--reset")

        self.assertEqual((counts(), balances()), first)

    def test_account_balances_match_ledger(self):
        run("--reset")
        paid = Transaction.objects.filter(status=Transaction.PaymentStatus.PAID)
        opening = {"Conta corrente": Decimal("3000.00"), "Poupança": Decimal("8000.00"),
                   "Vale benefício": Decimal("0.00")}

        for account in FinancialAccount.objects.all():
            def total(**filters):
                return paid.filter(account=account, **filters).aggregate(
                    t=Sum("amount"))["t"] or Decimal("0.00")

            expected = (
                opening[account.name]
                + total(transaction_type="income")
                - total(transaction_type="expense")
                - total(transaction_type="statement_payment")
                - (Transfer.objects.filter(from_account=account).aggregate(
                    t=Sum("amount"))["t"] or Decimal("0.00"))
                + (Transfer.objects.filter(destination_account=account).aggregate(
                    t=Sum("amount"))["t"] or Decimal("0.00"))
            )
            self.assertEqual(account.balance, expected, account.name)

    def test_paid_statement_matches_payment_transaction(self):
        run("--reset")
        statement = CardStatement.objects.get(status=CardStatement.StatementStatus.PAID)

        payment = Transaction.objects.get(
            transaction_type="statement_payment", statement=statement
        )

        self.assertEqual(payment.amount, statement.paid_amount)
        self.assertEqual(statement.paid_amount, statement.closed_amount)

    def test_reset_preserves_users(self):
        get_user_model().objects.create_user(username="lucas", password="x-12345678")

        run("--reset")

        self.assertTrue(get_user_model().objects.filter(username="lucas").exists())

    def test_refuses_without_reset_when_data_exists(self):
        run("--reset")
        before = counts()

        with self.assertRaises(CommandError):
            run()

        self.assertEqual(counts(), before)

    def test_runs_without_reset_on_empty_database(self):
        run()

        self.assertEqual(counts()["Transaction"], 47)


@override_settings(DEBUG=False)
class SeedDemoDataSafetyTests(TestCase):
    def test_refuses_when_debug_is_off_and_writes_nothing(self):
        Institution.objects.create(name="Real", code="001")
        before = counts()

        with self.assertRaises(CommandError):
            run("--reset")

        self.assertEqual(counts(), before)
