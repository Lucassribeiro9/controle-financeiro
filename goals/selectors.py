"""Seletores para as funcionalidades de objetivos e metas."""

from .models import Goal, MonthlyGoal
from .services import calculate_goal_progress


def _build_goal_summary(*, goal: Goal, year: int, month: int) -> dict:
    """Monta um resumo de objetivo com progresso calculado."""

    return {
        "goal": goal,
        "progress": calculate_goal_progress(goal=goal, year=year, month=month),
        "monthly_goals": list(
            goal.monthly_goals.filter(year=year, month=month).order_by("month")
        ),
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


def get_monthly_goals_for_period(*, year: int, month: int):
    """Lista metas mensais de um periodo."""

    return (
        MonthlyGoal.objects.filter(year=year, month=month)
        .select_related("goal", "goal__category")
        .prefetch_related("goal__accounts")
        .order_by("status", "goal__name")
    )


def get_goal_detail(*, goal_id: int, year: int, month: int) -> dict:
    """Retorna detalhe de um objetivo com progresso e metas do periodo."""

    goal = (
        Goal.objects.select_related("category")
        .prefetch_related("accounts", "monthly_goals")
        .get(pk=goal_id)
    )
    return _build_goal_summary(goal=goal, year=year, month=month)
