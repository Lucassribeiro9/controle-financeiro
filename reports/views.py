"""Views do app reports."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .selectors import get_monthly_dashboard


def _get_period_from_request(request: HttpRequest) -> tuple[int, int]:
    """Extrai ano e mes da query string ou usa o mes atual."""

    today = timezone.localdate()
    year = int(request.GET.get("year") or today.year)
    month = int(request.GET.get("month") or today.month)
    return year, month


def _render_monthly_dashboard(
    request: HttpRequest,
    *,
    year: int,
    month: int,
) -> HttpResponse:
    """Renderiza o dashboard mensal para o periodo informado."""

    context = get_monthly_dashboard(year=year, month=month)
    return render(request, "reports/monthly_dashboard.html", context)


def monthly_dashboard(request: HttpRequest, year: int, month: int) -> HttpResponse:
    """Exibe o painel financeiro mensal."""

    return _render_monthly_dashboard(request, year=year, month=month)


def monthly_dashboard_page(request: HttpRequest) -> HttpResponse:
    """Exibe o painel mensal usando periodo informado por filtro."""

    year, month = _get_period_from_request(request)
    return _render_monthly_dashboard(request, year=year, month=month)
