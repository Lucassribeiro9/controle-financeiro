"""Views do app reports."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .selectors import get_monthly_dashboard


def monthly_dashboard(request: HttpRequest, year: int, month: int) -> HttpResponse:
    """Exibe o painel financeiro mensal."""

    context = get_monthly_dashboard(year=year, month=month)
    return render(request, "reports/monthly_dashboard.html", context)
