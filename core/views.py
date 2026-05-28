"""Views do app core."""

from django.http import HttpResponse
from django.shortcuts import render

from core.selectors import get_operational_home_context


def health_check(request):
    return HttpResponse("OK")


def home(request):
    """Exibe a pagina inicial da aplicacao."""

    context = get_operational_home_context()
    return render(request, "core/home.html", context)
