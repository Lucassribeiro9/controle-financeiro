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
