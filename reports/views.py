"""Views do app reports."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from core.periods import get_period_from_request
from .selectors import get_monthly_dashboard


def _get_range_from_request(request: HttpRequest) -> int:
    """Extrai o intervalo do grafico da query string."""

    try:
        return int(request.GET.get("range") or 12)
    except ValueError:
        return 12


def _render_monthly_dashboard(
    request: HttpRequest,
    *,
    year: int,
    month: int,
) -> HttpResponse:
    """Renderiza o dashboard mensal para o periodo informado."""

    range_months = _get_range_from_request(request)
    context = get_monthly_dashboard(
        year=year,
        month=month,
        range_months=range_months,
    )
    return render(request, "reports/monthly_dashboard.html", context)


def monthly_dashboard(request: HttpRequest, year: int, month: int) -> HttpResponse:
    """Exibe o painel financeiro mensal."""

    return _render_monthly_dashboard(request, year=year, month=month)


def monthly_dashboard_page(request: HttpRequest) -> HttpResponse:
    """Exibe o painel mensal usando periodo informado por filtro."""

    year, month = get_period_from_request(request)
    return _render_monthly_dashboard(request, year=year, month=month)
