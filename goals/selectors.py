"""Seletores para as funcionalidades de objetivos e metas."""

from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import Goal, MonthlyGoal
from .services import calculate_goal_progress, calculate_monthly_goal_status


def apply_calculated_status(monthly_goals) -> list[MonthlyGoal]:
    """Preenche valor atual e status em memoria, sem gravar (ADR-012/016).

    Se o calculo falhar (ex.: objetivo antigo com moedas misturadas), mantem
    o valor gravado para a tela nao quebrar.
    """

    result = list(monthly_goals)
    for monthly_goal in result:
        try:
            monthly_goal.current_amount, monthly_goal.status = (
                calculate_monthly_goal_status(monthly_goal)
            )
        except ValidationError:
            pass
    return result


def _sort_by_status_and_name(monthly_goals: list[MonthlyGoal]) -> list[MonthlyGoal]:
    """Ordena por status (valor do campo) e nome do objetivo, como antes."""

    return sorted(
        monthly_goals, key=lambda item: (item.status, item.goal.name.casefold())
    )


def _build_goal_summary(*, goal: Goal, year: int, month: int) -> dict:
    """Monta um resumo de objetivo com progresso calculado."""

    try:
        progress = calculate_goal_progress(goal=goal, year=year, month=month)
    except ValidationError as exc:
        # Dado antigo inconsistente (ex.: moedas misturadas): nao quebra a tela.
        zero = Decimal("0.00")
        progress = {
            "current_amount": zero,
            "target_amount": goal.target_amount,
            "remaining_amount": goal.target_amount,
            "progress_percent": zero,
            "error": " ".join(exc.messages),
        }

    monthly_goals = goal.monthly_goals.filter(year=year, month=month).select_related(
        "goal"
    )
    return {
        "goal": goal,
        "progress": progress,
        "monthly_goals": apply_calculated_status(monthly_goals.order_by("month")),
    }


def get_active_goals(*, year: int, month: int) -> list[dict]:
    """Lista objetivos ativos com progresso para o periodo informado."""

    goals = (
        Goal.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("accounts", "monthly_goals")
        .order_by("name")
    )

    return [
        _build_goal_summary(goal=goal, year=year, month=month)
        for goal in goals
    ]


def get_monthly_goals_with_status(*, year: int, month: int) -> list[MonthlyGoal]:
    """Lista metas mensais do periodo com status calculado na leitura.

    Ponto unico de calculo para metas, detalhe e relatorios; nao grava.
    """

    monthly_goals = MonthlyGoal.objects.filter(year=year, month=month).select_related(
        "goal", "goal__category"
    )
    return _sort_by_status_and_name(apply_calculated_status(monthly_goals))


def get_goal_detail(*, goal_id: int, year: int, month: int) -> dict:
    """Retorna detalhe de um objetivo com progresso e metas do periodo."""

    goal = (
        Goal.objects.select_related("category")
        .prefetch_related("accounts", "monthly_goals")
        .get(pk=goal_id)
    )
    return _build_goal_summary(goal=goal, year=year, month=month)
