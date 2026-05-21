"""Views do app core."""

from django.http import HttpResponse
from django.shortcuts import render


def health_check(request):
    return HttpResponse("OK")


def home(request):
    """Exibe a pagina inicial da aplicacao."""

    return render(request, "core/home.html")
