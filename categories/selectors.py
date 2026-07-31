"""Selectors do app categories."""

from datetime import date
from decimal import Decimal

from django.db import models
from django.db.models import Q, QuerySet, Sum, Subquery, OuterRef, ExpressionWrapper, F
from django.db.models.functions import Coalesce

from categories.models import Category
from goals.models import Goal, MonthlyGoal
from transactions.models import Transaction


def get_categories_with_monthly_spent(
    reference_date: date,
) -> QuerySet[Category]:
    """Retorna categorias anotadas com o gasto e limite do mes de referencia.

    Considera apenas transacoes de despesa (expense, card_purchase,
    benefit_purchase) com status efetivo (exclui canceled, ignored,
    forecasted). Cada categoria recebe o atributo ``monthly_spent``
    com valor Decimal; categorias sem gasto retornam Decimal('0.00').
    Tambem recebe ``limit_amount`` caso haja meta de reducao ativa.
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

    monthly_goals_subquery = MonthlyGoal.objects.filter(
        goal__goal_type=Goal.GoalType.REDUCTION,
        goal__category=OuterRef("pk"),
        year=reference_date.year,
        month=reference_date.month,
    )

    return (
        Category.objects.select_related("parent")
        .annotate(
            limit_amount=Subquery(
                monthly_goals_subquery.values("target_amount")[:1]
            ),
            monthly_spent=Coalesce(
                Sum("transactions__amount", filter=expense_filter),
                Decimal("0.00"),
                output_field=models.DecimalField(),
            ),
        )
    )


def get_categories_at_risk(reference_date: date) -> QuerySet[Category]:
    """Retorna categorias que estao em risco (>=80% do limite) ou excedidas."""
    limit_at_risk_expression = ExpressionWrapper(
        F("limit_amount") * Decimal("0.80"),
        output_field=models.DecimalField(max_digits=14, decimal_places=2),
    )
    return get_categories_with_monthly_spent(reference_date).filter(
        limit_amount__isnull=False,
        monthly_spent__gte=limit_at_risk_expression,
    )


