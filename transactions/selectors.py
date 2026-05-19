"""Seletores para leitura/consulda de dados relacionados a transações financeiras."""

from django.db.models import Sum
from decimal import Decimal
from .models import Transaction, Transfer

# Status excluídos para não serem considerados nos cálculos
EXCLUDED_STATUSES = [
    Transaction.PaymentStatus.IGNORED,
    Transaction.PaymentStatus.CANCELED,
    Transaction.PaymentStatus.FORECASTED,
]


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
        transaction_type=Transaction.TransactionType.EXPENSE,
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
