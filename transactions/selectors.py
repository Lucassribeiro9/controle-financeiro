"""Seletores para leitura/consulta de dados relacionados a transações financeiras."""

from decimal import Decimal

from django.db.models import Sum

from accounts.models import FinancialAccount

from .models import Transaction, Transfer

# Status excluídos para não serem considerados nos cálculos
EXCLUDED_STATUSES = [
    Transaction.PaymentStatus.IGNORED,
    Transaction.PaymentStatus.CANCELED,
    Transaction.PaymentStatus.FORECASTED,
]
EXPENSE_TRANSACTION_TYPES = [
    Transaction.TransactionType.EXPENSE,
    Transaction.TransactionType.BENEFIT_PURCHASE,
]


def get_account_balance(*, account=None, account_id=None):
    """Retorna o saldo persistido de uma conta financeira."""

    if (account is None and account_id is None) or (
        account is not None and account_id is not None
    ):
        raise ValueError("Informe account ou account_id.")

    selected_account_id = account_id
    if account is not None:
        if account.pk is None:
            raise ValueError("Conta precisa estar persistida.")
        selected_account_id = account.pk

    return FinancialAccount.objects.only("balance").get(pk=selected_account_id).balance


def get_monthly_income_total(*, year, month):
    """Calcula o total de renda mensal."""
    total = Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.INCOME,
        date__year=year,
        date__month=month,
    ).exclude(status__in=EXCLUDED_STATUSES).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal(
        "0.00"
    )
    return total


def get_monthly_expense_total(*, year, month):
    """Calcula o total de despesas mensais."""
    total = Transaction.objects.filter(
        transaction_type__in=EXPENSE_TRANSACTION_TYPES,
        date__year=year,
        date__month=month,
    ).exclude(status__in=EXCLUDED_STATUSES).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal(
        "0.00"
    )
    return total


def get_monthly_transfers_total(*, year, month):
    """Calcula o total de transferências internas mensais."""
    total = Transfer.objects.filter(
        date__year=year,
        date__month=month,
    ).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal(
        "0.00"
    )
    return total


def get_transactions_for_period(*, year, month):
    """Lista transacoes de um periodo com relacionamentos principais."""

    return (
        Transaction.objects.filter(date__year=year, date__month=month)
        .select_related("account", "category", "card", "statement")
        .order_by("-date", "-created_at")
    )


def get_filtered_transactions(*, year, month, status=None, transaction_type=None):
    """Lista transacoes de um periodo aplicando filtros opcionais."""

    transactions = get_transactions_for_period(year=year, month=month)

    if status:
        transactions = transactions.filter(status=status)

    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    return transactions


def get_recent_transactions(*, limit=10):
    """Lista transacoes recentes para telas de acompanhamento."""

    return (
        Transaction.objects.select_related("account", "category", "card", "statement")
        .order_by("-date", "-created_at")[:limit]
    )


def get_transactions_by_status(*, status):
    """Lista transacoes filtradas por status."""

    return (
        Transaction.objects.filter(status=status)
        .select_related("account", "category", "card", "statement")
        .order_by("-date", "-created_at")
    )


def get_transactions_by_type(*, transaction_type):
    """Lista transacoes filtradas por tipo."""

    return (
        Transaction.objects.filter(transaction_type=transaction_type)
        .select_related("account", "category", "card", "statement")
        .order_by("-date", "-created_at")
    )


def get_transfers_for_period(*, year, month):
    """Lista transferencias de um periodo com contas carregadas."""

    return (
        Transfer.objects.filter(date__year=year, date__month=month)
        .select_related("from_account", "destination_account")
        .order_by("-date", "-created_at")
    )
