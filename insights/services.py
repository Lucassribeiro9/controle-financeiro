"""Regras de negocio para os insights."""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum

from goals.models import Goal
from goals.services import create_monthly_goal_from_goal
from insights.models import IgnoredPattern, Insight
from transactions.models import Transaction


def _build_monthly_source_key(*, prefix, object_id, year, month):
    """Monta chave unica para evitar insight duplicado no mesmo mes."""

    return f"{prefix}:{object_id}:{year}-{month:02d}"


def _build_pattern_key(*, prefix, object_id):
    """Monta chave generica para silenciar sugestoes futuras."""

    return f"{prefix}:{object_id}"


def _get_pattern_key_from_source_key(source_key):
    """Extrai uma chave generica a partir de uma chave mensal."""

    if not source_key:
        return ""

    parts = source_key.split(":")
    if len(parts) >= 2:
        return ":".join(parts[:2])

    return source_key


def get_category_expense_total(*, category, year, month):
    """Calcula o total gasto em uma categoria."""
    total = Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.EXPENSE,
        status=Transaction.PaymentStatus.PAID,
        category=category,
        date__year=year,
        date__month=month,
    ).exclude(
        status__in=[
            Transaction.PaymentStatus.CANCELED,
            Transaction.PaymentStatus.IGNORED,
            Transaction.PaymentStatus.FORECASTED,
        ]
    ).aggregate(total_amount=Sum("amount"))["total_amount"] or Decimal("0.00")
    return total

def suggest_category_limit(*, category, year, month):
    """Sugere um limite para a categoria."""
    total = get_category_expense_total(category=category, year=year, month=month)

    if total <= Decimal("0.00"):
        return None

    suggested_amount = total.quantize(Decimal("0.01"))
    source_key = _build_monthly_source_key(
        prefix="category-limit",
        object_id=category.id,
        year=year,
        month=month,
    )
    pattern_key = _build_pattern_key(prefix="category-limit", object_id=category.id)

    if Insight.objects.filter(source_key=source_key).exists():
        return None
    if IgnoredPattern.objects.filter(pattern_key=pattern_key).exists():
        return None

    return Insight.objects.create(
        title=f"Limite sugerido para {category.name}",
        message=(
            f"Neste mês, os gastos em {category.name} estão em R$ {total}. "
            f"Você pode criar uma meta mensal para acompanhar essa categoria com mais calma."
        ),
        insight_type=Insight.InsightType.CATEGORY_LIMIT,
        category=category,
        suggested_amount=suggested_amount,
        source_key=source_key,
    )


def approve_insight(*, insight):
    """Aprova um insight."""
    if insight.status != Insight.Status.PENDING:
        return insight

    if insight.insight_type == Insight.InsightType.CATEGORY_LIMIT:
        goal = Goal.objects.create(
            name=f"Limite: {insight.category.name}",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=insight.suggested_amount,
            start_date=date.today(),
            category=insight.category,
        )
        monthly_goal = create_monthly_goal_from_goal(
            goal=goal,
            year=date.today().year,
            month=date.today().month,
            target_amount=insight.suggested_amount,
        )
        insight.monthly_goal = monthly_goal

    insight.status = Insight.Status.APPROVED
    insight.full_clean()
    insight.save()
    return insight


def ignore_insight(*, insight):
    """Ignora um insight."""
    insight.status = Insight.Status.IGNORED
    insight.full_clean()
    insight.save(update_fields=["status", "updated_at"])
    return insight


def silence_insight(*, insight):
    """Silencia um insight."""
    if insight.source_key:
        IgnoredPattern.objects.get_or_create(
            pattern_key=_get_pattern_key_from_source_key(insight.source_key)
        )

    insight.status = Insight.Status.SILENCED
    insight.full_clean()
    insight.save(update_fields=["status", "updated_at"])
    return insight


def detect_recurrent_habits(*, year, month):
    """Detecta hábitos recorrentes."""
    expenses = Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.EXPENSE,
        status=Transaction.PaymentStatus.PAID,
        date__year=year,
        date__month=month,
    ).exclude(
        status__in=[
            Transaction.PaymentStatus.CANCELED,
            Transaction.PaymentStatus.IGNORED,
            Transaction.PaymentStatus.FORECASTED,
        ]
    )

    created = []
    grouped = (
        expenses.values("category_id", "category__name")
        .annotate(total_amount=Sum("amount"), count=Count("id"))
        .filter(count__gte=3)  # Considera recorrente se tiver 3 ou
    )
    for item in grouped:
        source_key = _build_monthly_source_key(
            prefix="habit-category",
            object_id=item["category_id"],
            year=year,
            month=month,
        )
        pattern_key = _build_pattern_key(
            prefix="habit-category",
            object_id=item["category_id"],
        )

        if Insight.objects.filter(source_key=source_key).exists():
            continue
        if IgnoredPattern.objects.filter(pattern_key=pattern_key).exists():
            continue

        insight = Insight.objects.create(
            title=f"Hábito recorrente em {item['category__name']}",
            message=(
                f"Identifiquei {item['count']} gastos em {item['category__name']} "
                f"neste mês, somando R$ {item['total_amount']}. Talvez valha acompanhar "
                f"essa categoria com uma meta leve."
            ),
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            category_id=item["category_id"],
            suggested_amount=item["total_amount"]
            / item["count"],  # Média para sugerir uma meta
            source_key=source_key,
        )
        created.append(insight)
    return created
