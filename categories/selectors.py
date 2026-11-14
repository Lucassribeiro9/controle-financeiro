"""Selectors do app categories."""

from datetime import date
from decimal import Decimal

from django.db import models
from django.db.models import Count, Q, QuerySet, Sum, Subquery, OuterRef, ExpressionWrapper, F
from django.db.models.functions import Coalesce

from categories.models import Category
from goals.models import Goal, MonthlyGoal
from transactions.constants import (
    EXCLUDED_SPENDING_STATUSES,
    SPENDING_TRANSACTION_TYPES,
)


def get_categories_with_monthly_spent(
    reference_date: date,
) -> QuerySet[Category]:
    """Retorna categorias anotadas com o gasto e limite do mes de referencia.

    Considera apenas transacoes de despesa (expense, card_purchase,
    benefit_purchase) com status efetivo (exclui canceled, ignored,
    forecasted). Cada categoria recebe o atributo ``monthly_spent``
    com valor Decimal; categorias sem gasto retornam Decimal('0.00').
    Tambem recebe ``limit_amount`` caso haja meta de reducao ativa; com mais
    de uma, vale a de menor ``goal_id`` (igual a ``get_reduction_monthly_goal``).
    """

    expense_filter = Q(
        transactions__transaction_type__in=SPENDING_TRANSACTION_TYPES,
        transactions__date__year=reference_date.year,
        transactions__date__month=reference_date.month,
    ) & ~Q(transactions__status__in=EXCLUDED_SPENDING_STATUSES)

    monthly_goals_subquery = MonthlyGoal.objects.filter(
        goal__goal_type=Goal.GoalType.REDUCTION,
        goal__category=OuterRef("pk"),
        goal__is_active=True,
        year=reference_date.year,
        month=reference_date.month,
    ).order_by("goal_id")

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


def get_categories_for_list(reference_date: date) -> QuerySet[Category]:
    """Retorna categorias da listagem com gasto mensal e contagem de filhos.

    ``children_count`` conta os filhos diretos (ativos ou inativos) por
    subquery, sem JOIN com ``children``, para nao multiplicar o
    ``monthly_spent`` de ``get_categories_with_monthly_spent``.
    """

    children_count = (
        Category.objects.filter(parent=OuterRef("pk"))
        .values("parent")
        .annotate(total=Count("pk"))
        .values("total")
    )
    return (
        get_categories_with_monthly_spent(reference_date)
        .annotate(children_count=Coalesce(Subquery(children_count), 0))
        .order_by("parent__name", "name")
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


