"""Tests dos seletores do app transactions."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from institutions.models import Institution
from transactions.models import Transaction, Transfer
from transactions.selectors import (
    get_account_balance,
    get_filtered_transactions,
    get_recent_transactions,
    get_monthly_expense_total,
    get_monthly_income_total,
    get_monthly_transfers_total,
    get_transactions_by_status,
    get_transactions_by_type,
    get_transactions_for_period,
    get_transfers_for_period,
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
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )
        self.benefit_card = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("300.00"),
            balance=Decimal("300.00"),
        )

    def test_get_account_balance_returns_balance_by_account(self):
        """Deve retornar o saldo persistido da conta informada."""

        balance = get_account_balance(account=self.account)

        self.assertEqual(balance, Decimal("1000.00"))

    def test_get_account_balance_returns_fresh_balance_by_account(self):
        """Deve buscar saldo atualizado no banco mesmo com instancia antiga."""

        FinancialAccount.objects.filter(pk=self.account.pk).update(
            balance=Decimal("1250.00")
        )

        balance = get_account_balance(account=self.account)

        self.assertEqual(balance, Decimal("1250.00"))

    def test_get_account_balance_returns_balance_by_account_id(self):
        """Deve retornar o saldo usando o id da conta."""

        balance = get_account_balance(account_id=self.destination_account.id)

        self.assertEqual(balance, Decimal("200.00"))

    def test_get_account_balance_requires_account_or_account_id(self):
        """Deve exigir uma forma clara de identificar a conta."""

        with self.assertRaisesMessage(ValueError, "Informe account ou account_id."):
            get_account_balance()

    def test_get_account_balance_rejects_ambiguous_input(self):
        """Nao deve aceitar account e account_id ao mesmo tempo."""

        with self.assertRaisesMessage(ValueError, "Informe account ou account_id."):
            get_account_balance(account=self.account, account_id=self.account.id)

    def test_get_account_balance_rejects_unsaved_account(self):
        """Nao deve consultar saldo de conta sem registro persistido."""

        unsaved_account = FinancialAccount(
            name="Conta temporaria",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("10.00"),
        )

        with self.assertRaisesMessage(ValueError, "Conta precisa estar persistida."):
            get_account_balance(account=unsaved_account)

    def test_get_account_balance_raises_for_unknown_account_id(self):
        """Deve propagar erro quando a conta nao existir."""

        with self.assertRaises(FinancialAccount.DoesNotExist):
            get_account_balance(account_id=999999)

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
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Pagamento fatura",
            amount=Decimal("800.00"),
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 12),
        )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("250.00"))

    def test_get_monthly_expense_total_includes_benefit_purchase(self):
        """Compra de beneficio deve compor o total mensal de despesas."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Almoco",
            amount=Decimal("35.00"),
            transaction_type=Transaction.TransactionType.BENEFIT_PURCHASE,
            card=self.benefit_card,
            date=date(2026, 5, 9),
        )

        total = get_monthly_expense_total(year=2026, month=5)

        self.assertEqual(total, Decimal("285.00"))

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

    def test_transfer_does_not_affect_monthly_income_or_expense_totals(self):
        """Transferencia nao deve afetar totais mensais de receita/despesa."""

        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        self.assertEqual(get_monthly_income_total(year=2026, month=5), Decimal("0.00"))
        self.assertEqual(get_monthly_expense_total(year=2026, month=5), Decimal("0.00"))
        self.assertEqual(get_monthly_transfers_total(year=2026, month=5), Decimal("300.00"))

    def test_get_transfers_for_period_lists_month_items(self):
        """Deve listar transferencias do periodo informado."""

        may_transfer = Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )
        Transfer.objects.create(
            description="Outro mes",
            amount=Decimal("200.00"),
            from_account=self.account,
            destination_account=self.destination_account,
            date=date(2026, 6, 8),
        )

        transfers = list(get_transfers_for_period(year=2026, month=5))

        self.assertEqual(transfers, [may_transfer])

    def test_monthly_totals_return_zero_when_there_are_no_records(self):
        """Deve retornar Decimal zero quando nao houver registros."""

        self.assertEqual(get_monthly_income_total(year=2026, month=5), Decimal("0.00"))
        self.assertEqual(get_monthly_expense_total(year=2026, month=5), Decimal("0.00"))
        self.assertEqual(get_monthly_transfers_total(year=2026, month=5), Decimal("0.00"))

    def test_get_transactions_for_period_lists_month_items(self):
        """Deve listar transacoes do periodo informado."""

        may_transaction = Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
        )
        Transaction.objects.create(
            description="Outro mes",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 6, 8),
        )

        transactions = list(get_transactions_for_period(year=2026, month=5))

        self.assertEqual(transactions, [may_transaction])

    def test_get_recent_transactions_respects_limit(self):
        """Deve limitar a quantidade de transacoes recentes."""

        Transaction.objects.create(
            description="Primeira",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            date=date(2026, 5, 1),
        )
        latest = Transaction.objects.create(
            description="Ultima",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            date=date(2026, 5, 2),
        )

        transactions = list(get_recent_transactions(limit=1))

        self.assertEqual(transactions, [latest])

    def test_get_transactions_by_status_filters_status(self):
        """Deve filtrar transacoes por status."""

        paid = Transaction.objects.create(
            description="Paga",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 1),
        )
        Transaction.objects.create(
            description="Pendente",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.account,
            date=date(2026, 5, 2),
        )

        transactions = list(get_transactions_by_status(status=Transaction.PaymentStatus.PAID))

        self.assertEqual(transactions, [paid])

    def test_get_transactions_by_type_filters_type(self):
        """Deve filtrar transacoes por tipo."""

        card_purchase = Transaction.objects.create(
            description="Compra no cartao",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.card,
            date=date(2026, 5, 1),
        )
        Transaction.objects.create(
            description="Despesa",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 2),
        )

        transactions = list(
            get_transactions_by_type(
                transaction_type=Transaction.TransactionType.CARD_PURCHASE
            )
        )

        self.assertEqual(transactions, [card_purchase])

    def test_get_filtered_transactions_combines_period_status_and_type(self):
        """Deve combinar filtros de periodo, status e tipo."""

        matched = Transaction.objects.create(
            description="Compra no cartao",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PAID,
            card=self.card,
            date=date(2026, 5, 1),
        )
        Transaction.objects.create(
            description="Compra pendente",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            date=date(2026, 5, 1),
        )
        Transaction.objects.create(
            description="Outro mes",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PAID,
            card=self.card,
            date=date(2026, 6, 1),
        )

        transactions = list(
            get_filtered_transactions(
                year=2026,
                month=5,
                status=Transaction.PaymentStatus.PAID,
                transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            )
        )

        self.assertEqual(transactions, [matched])
