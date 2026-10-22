"""Regras de negocio para os insights."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, Sum

from categories.models import Category
from core.templatetags.money import brl, month_name
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


def _qualifying_expenses(*, year, month):
    """Despesas pagas e categorizadas do mes que contam para os insights."""

    return Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.EXPENSE,
        status=Transaction.PaymentStatus.PAID,
        category__isnull=False,
        date__year=year,
        date__month=month,
    )


def _month_label(*, year, month):
    """Formata o mes para mensagens, por exemplo Maio/2026."""

    return f"{month_name(month)}/{year}"


def get_category_expense_total(*, category, year, month):
    """Calcula o total gasto em uma categoria."""
    total = _qualifying_expenses(year=year, month=month).filter(
        category=category
    ).aggregate(total_amount=Sum("amount"))["total_amount"]
    return total or Decimal("0.00")


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
            f"Em {_month_label(year=year, month=month)}, os gastos em "
            f"{category.name} somam {brl(total)}. "
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
        if insight.category is None:
            raise ValidationError("A categoria deste insight não existe mais.")
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
    """Detecta categorias com tres ou mais despesas pagas no mes."""
    created = []
    grouped = (
        _qualifying_expenses(year=year, month=month)
        .values("category_id", "category__name")
        .annotate(total_amount=Sum("amount"), count=Count("id"))
        .filter(count__gte=3)
        .order_by("category__name")
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
                f"Em {_month_label(year=year, month=month)}, identifiquei "
                f"{item['count']} gastos em {item['category__name']}, somando "
                f"{brl(item['total_amount'])}. Talvez valha acompanhar essa "
                f"categoria com uma meta leve."
            ),
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            category_id=item["category_id"],
            suggested_amount=(item["total_amount"] / item["count"]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            source_key=source_key,
        )
        created.append(insight)
    return created


def generate_monthly_insights(*, year, month):
    """Gera os insights do mes e devolve apenas os criados agora."""
    category_ids = (
        _qualifying_expenses(year=year, month=month)
        .values_list("category_id", flat=True)
        .distinct()
    )
    created = []
    for category in Category.objects.filter(id__in=category_ids).order_by("name"):
        insight = suggest_category_limit(category=category, year=year, month=month)
        if insight is not None:
            created.append(insight)
    created.extend(detect_recurrent_habits(year=year, month=month))
    return created
