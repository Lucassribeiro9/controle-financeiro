"""Selectors do app categories."""

from datetime import date
from decimal import Decimal

from django.db import models
from django.db.models import Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from categories.models import Category
from transactions.models import Transaction


def get_categories_with_monthly_spent(
    reference_date: date,
) -> QuerySet[Category]:
    """Retorna categorias anotadas com o gasto do mes de referencia.

    Considera apenas transacoes de despesa (expense, card_purchase,
    benefit_purchase) com status efetivo (exclui canceled, ignored,
    forecasted). Cada categoria recebe o atributo ``monthly_spent``
    com valor Decimal; categorias sem gasto retornam Decimal('0.00').
    """

    expense_types = [
        Transaction.TransactionType.EXPENSE,
        Transaction.TransactionType.CARD_PURCHASE,
        Transaction.TransactionType.BENEFIT_PURCHASE,
    ]

    excluded_statuses = [
        Transaction.PaymentStatus.CANCELED,
        Transaction.PaymentStatus.IGNORED,
        Transaction.PaymentStatus.FORECASTED,
    ]

    expense_filter = Q(
        transactions__transaction_type__in=expense_types,
        transactions__date__year=reference_date.year,
        transactions__date__month=reference_date.month,
    ) & ~Q(transactions__status__in=excluded_statuses)

    return (
        Category.objects.select_related("parent")
        .annotate(
            monthly_spent=Coalesce(
                Sum("transactions__amount", filter=expense_filter),
                Decimal("0.00"),
                output_field=models.DecimalField(),
            ),
        )
    )
