from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from transactions.models import Transaction

from .models import Goal, MonthlyGoal


EXCLUDED_TRANSACTION_STATUSES = [
    Transaction.PaymentStatus.IGNORED,
    Transaction.PaymentStatus.CANCELED,
    Transaction.PaymentStatus.FORECASTED,
]


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
            transaction_type=Transaction.TransactionType.EXPENSE,
            category=goal.category,
            date__year=year,
            date__month=month,
        )
        .exclude(status__in=EXCLUDED_TRANSACTION_STATUSES)
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
                    "period": "Objetivos de reducao exigem ano e mes para calcular progresso."
                }
            )
        current_amount = _get_reduction_current_amount(
            goal=goal,
            year=year,
            month=month,
        )
    else:
        raise ValidationError({"goal_type": "Tipo de objetivo invalido."})

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


def update_monthly_goal_status(monthly_goal: MonthlyGoal) -> MonthlyGoal:
    """Atualiza valor atual e status de uma meta mensal."""

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

    monthly_goal.current_amount = current_amount
    monthly_goal.status = status
    monthly_goal.full_clean()
    monthly_goal.save(update_fields=["current_amount", "status"])

    return monthly_goal
