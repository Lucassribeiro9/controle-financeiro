from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from categories.models import Category
from core.templatetags.money import month_name
from transactions.constants import (
    EXCLUDED_SPENDING_STATUSES,
    SPENDING_TRANSACTION_TYPES,
)
from transactions.models import Transaction

from .models import Goal, MonthlyGoal


def _zero() -> Decimal:
    """Retorna zero monetario padronizado."""

    return Decimal("0.00")


def _percent(*, current_amount: Decimal, target_amount: Decimal) -> Decimal:
    """Calcula percentual com duas casas decimais."""

    if target_amount <= _zero():
        return _zero()

    return ((current_amount / target_amount) * Decimal("100.00")).quantize(
        Decimal("0.01")
    )


def _get_accumulation_current_amount(goal: Goal) -> Decimal:
    """Soma o saldo das contas vinculadas ao objetivo de acumulo."""

    total = goal.accounts.aggregate(total=Sum("balance"))["total"]
    return total or _zero()


def _get_reduction_current_amount(*, goal: Goal, year: int, month: int) -> Decimal:
    """Soma despesas reais da categoria vinculada no mes informado."""

    if not goal.category_id:
        raise ValidationError(
            {"category": "Objetivos de reducao exigem categoria vinculada."}
        )

    total = (
        Transaction.objects.filter(
            transaction_type__in=SPENDING_TRANSACTION_TYPES,
            category=goal.category,
            date__year=year,
            date__month=month,
        )
        .exclude(status__in=EXCLUDED_SPENDING_STATUSES)
        .aggregate(total=Sum("amount"))["total"]
    )
    return total or _zero()


def calculate_goal_progress(
    *, goal: Goal, year: int | None = None, month: int | None = None
) -> dict:
    """Calcula progresso de objetivo de acumulo ou reducao."""

    if goal.goal_type == Goal.GoalType.ACCUMULATION:
        current_amount = _get_accumulation_current_amount(goal)
    elif goal.goal_type == Goal.GoalType.REDUCTION:
        if year is None or month is None:
            raise ValidationError(
                {
                    "period": "Objetivos de redução exigem ano e mês para calcular progresso."
                }
            )
        current_amount = _get_reduction_current_amount(
            goal=goal,
            year=year,
            month=month,
        )
    else:
        raise ValidationError({"goal_type": "Tipo de objetivo inválido."})

    progress_percent = _percent(
        current_amount=current_amount,
        target_amount=goal.target_amount,
    )
    remaining_amount = max(goal.target_amount - current_amount, _zero())

    return {
        "current_amount": current_amount,
        "target_amount": goal.target_amount,
        "remaining_amount": remaining_amount,
        "progress_percent": progress_percent,
    }


def create_monthly_goal_from_goal(
    *, goal: Goal, year: int, month: int, target_amount: Decimal | None = None
) -> MonthlyGoal:
    """Cria uma meta mensal a partir de um objetivo financeiro."""

    monthly_goal = MonthlyGoal(
        goal=goal,
        year=year,
        month=month,
        target_amount=target_amount or goal.target_amount,
    )
    monthly_goal.full_clean()
    monthly_goal.save()
    return monthly_goal


def create_monthly_goal(goal, year, month, target_amount=None):
    """Compatibilidade com o nome inicial do servico."""

    return create_monthly_goal_from_goal(
        goal=goal,
        year=year,
        month=month,
        target_amount=target_amount,
    )


def calculate_monthly_goal_status(monthly_goal: MonthlyGoal) -> tuple[Decimal, str]:
    """Calcula valor atual e status da meta mensal sem gravar nada."""

    progress = calculate_goal_progress(
        goal=monthly_goal.goal,
        year=monthly_goal.year,
        month=monthly_goal.month,
    )
    current_amount = progress["current_amount"]
    target_amount = monthly_goal.target_amount

    if monthly_goal.goal.goal_type == Goal.GoalType.ACCUMULATION:
        if current_amount >= target_amount:
            status = MonthlyGoal.Status.ACHIEVED
        else:
            status = MonthlyGoal.Status.ON_TRACK
    else:
        risk_threshold = target_amount * Decimal("0.80")
        if current_amount >= target_amount:
            status = MonthlyGoal.Status.MISSED
        elif current_amount >= risk_threshold:
            status = MonthlyGoal.Status.AT_RISK
        else:
            status = MonthlyGoal.Status.ON_TRACK

    return current_amount, status


def update_monthly_goal_status(monthly_goal: MonthlyGoal) -> MonthlyGoal:
    """Recalcula e persiste valor atual e status de uma meta mensal."""

    with transaction.atomic():
        locked = MonthlyGoal.objects.select_for_update().get(pk=monthly_goal.pk)
        current_amount, status = calculate_monthly_goal_status(locked)
        locked.current_amount = current_amount
        locked.status = status
        locked.full_clean()
        locked.save(update_fields=["current_amount", "status"])

    monthly_goal.current_amount = locked.current_amount
    monthly_goal.status = locked.status
    return monthly_goal


def refresh_monthly_goals(*, year: int, month: int) -> int:
    """Recalcula e persiste todas as metas mensais do periodo."""

    count = 0
    for monthly_goal in MonthlyGoal.objects.filter(year=year, month=month).order_by("pk"):
        update_monthly_goal_status(monthly_goal)
        count += 1
    return count


@transaction.atomic
def get_or_create_reduction_goal(*, category: Category, target_amount: Decimal) -> Goal:
    """Retorna o Goal de reducao da categoria, criando-o se nao existir.

    Trava a categoria para que duas chamadas concorrentes nao criem dois Goals.
    Se houver duplicatas antigas, reutiliza a mais antiga em vez de falhar.
    """

    Category.objects.select_for_update().get(pk=category.pk)
    goal = (
        Goal.objects.filter(goal_type=Goal.GoalType.REDUCTION, category=category)
        .order_by("pk")
        .first()
    )
    if goal is not None:
        return goal

    goal = Goal(
        name=f"Limite - {category.name}",
        goal_type=Goal.GoalType.REDUCTION,
        category=category,
        target_amount=target_amount,
        start_date=timezone.localdate(),
    )
    goal.full_clean()
    goal.save()
    return goal


def get_reduction_monthly_goal(
    *, category: Category, year: int, month: int
) -> MonthlyGoal | None:
    """Retorna a meta mensal de reducao da categoria no mes, travada para escrita."""

    return (
        MonthlyGoal.objects.select_for_update()
        .filter(
            goal__goal_type=Goal.GoalType.REDUCTION,
            goal__category=category,
            year=year,
            month=month,
        )
        .order_by("goal_id")
        .first()
    )


@transaction.atomic
def create_reduction_goal_for_category(
    *,
    category: Category,
    year: int,
    month: int,
    target_amount: Decimal,
) -> MonthlyGoal:
    """Cria ou reutiliza Goal de reducao para categoria e gera MonthlyGoal.

    Regras:
    - Um unico Goal de reducao por categoria (get_or_create).
    - Um MonthlyGoal por ano/mes (unique_together no model).
    - Valor negativo ou zero e invalido.
    - Transacao atomica: se MonthlyGoal falhar, Goal nao e persistido.
    """

    if target_amount <= Decimal("0.00"):
        raise ValidationError(
            {"target_amount": "O valor da meta deve ser positivo."}
        )

    goal = get_or_create_reduction_goal(category=category, target_amount=target_amount)

    if MonthlyGoal.objects.filter(goal=goal, year=year, month=month).exists():
        raise ValidationError(
            f"Já existe uma meta para {category.name} em {month_name(month)}/{year}."
        )

    return create_monthly_goal_from_goal(
        goal=goal,
        year=year,
        month=month,
        target_amount=target_amount,
    )
