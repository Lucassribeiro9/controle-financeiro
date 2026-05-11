"""Tests dos seletores do app transactions."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from transactions.models import Transaction, Transfer
from transactions.selectors import (
    get_monthly_expense_total,
    get_monthly_income_total,
    get_monthly_transfers_total,
)


class TransactionSelectorTests(TestCase):
    """Garante os totais mensais de transacoes e transferencias."""

    def setUp(self):
        """Cria contas base para os cenarios dos seletores."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
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

    def test_get_monthly_income_total_sums_income_from_given_month(self):
        """Deve somar receitas do mes informado."""

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Freela",
            amount=Decimal("750.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            date=date(2026, 5, 15),
        )

        total = get_monthly_income_total(year=2026, month=5)

        self.assertEqual(total, Decimal("5750.00"))

    def test_get_monthly_income_total_ignores_income_from_other_month(self):
        """Nao deve somar receitas de outro mes."""

        Transaction.objects.create(
            description="Salario maio",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Salario junho",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            date=date(2026, 6, 8),
        )

        total = get_monthly_income_total(year=2026, month=5)

        self.assertEqual(total, Decimal("5000.00"))

    def test_get_monthly_expense_total_sums_expenses_from_given_month(self):
        """Deve somar despesas do mes informado."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Internet",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 10),
        )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("350.00"))

    def test_get_monthly_expense_total_does_not_include_statement_payment(self):
        """Nao deve incluir pagamento de fatura como despesa mensal."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Pagamento fatura",
            amount=Decimal("800.00"),
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            account=self.account,
            date=date(2026, 5, 12),
        )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("250.00"))

    def test_monthly_totals_ignore_canceled_ignored_and_forecasted_transactions(self):
        """Nao deve somar transacoes canceladas, ignoradas ou previstas."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Despesa cancelada",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.CANCELED,
            account=self.account,
            date=date(2026, 5, 9),
        )
        Transaction.objects.create(
            description="Despesa ignorada",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.IGNORED,
            account=self.account,
            date=date(2026, 5, 10),
        )
        Transaction.objects.create(
            description="Despesa prevista",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 5, 11),
        )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("250.00"))

    def test_get_monthly_transfers_total_sums_transfers_using_transfer_model(self):
        """Deve somar transferencias usando o model Transfer."""

        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )
        Transfer.objects.create(
            description="Aporte viagem",
            amount=Decimal("150.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 5, 15),
        )
        Transfer.objects.create(
            description="Aporte outro mes",
            amount=Decimal("200.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 6, 8),
        )

        total = get_monthly_transfers_total(year=2026, month=5)

        self.assertEqual(total, Decimal("450.00"))

    def test_monthly_totals_return_zero_when_there_are_no_records(self):
        """Deve retornar Decimal zero quando nao houver registros."""

        self.assertEqual(get_monthly_income_total(year=2026, month=5), Decimal("0.00"))
        self.assertEqual(get_monthly_expense_total(year=2026, month=5), Decimal("0.00"))
        self.assertEqual(get_monthly_transfers_total(year=2026, month=5), Decimal("0.00"))
