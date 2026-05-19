"""Views do app goals."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .selectors import get_active_goals, get_goal_detail, get_monthly_goals_for_period
from .services import update_monthly_goal_status


def _get_period_from_request(request: HttpRequest) -> tuple[int, int]:
    """Extrai ano e mes da query string ou usa o mes atual."""

    today = timezone.localdate()
    year = int(request.GET.get("year") or today.year)
    month = int(request.GET.get("month") or today.month)
    return year, month


def goal_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de objetivos ativos com progresso."""

    year, month = _get_period_from_request(request)
    goal_summaries = get_active_goals(year=year, month=month)

    return render(
        request,
        "goals/list.html",
        {
            "year": year,
            "month": month,
            "goal_summaries": goal_summaries,
        },
    )


def monthly_goals_page(request: HttpRequest) -> HttpResponse:
    """Renderiza metas mensais do periodo informado."""

    year, month = _get_period_from_request(request)
    monthly_goals = list(get_monthly_goals_for_period(year=year, month=month))
    monthly_goals = [
        update_monthly_goal_status(monthly_goal)
        for monthly_goal in monthly_goals
    ]

    return render(
        request,
        "goals/monthly_goals.html",
        {
            "year": year,
            "month": month,
            "monthly_goals": monthly_goals,
        },
    )


def goal_detail_page(request: HttpRequest, goal_id: int) -> HttpResponse:
    """Renderiza o detalhe de um objetivo com progresso e metas do periodo."""

    year, month = _get_period_from_request(request)
    goal_summary = get_goal_detail(goal_id=goal_id, year=year, month=month)

    return render(
        request,
        "goals/detail.html",
        {
            "year": year,
            "month": month,
            "goal_summary": goal_summary,
        },
    )
