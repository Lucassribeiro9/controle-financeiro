"""Views do app core."""

from django.http import Http404, HttpResponse
from django.shortcuts import render

from core.selectors import (
    SUMMARY_CARD_LABELS,
    get_operational_home_context,
    get_summary_card_detail,
)


def health_check(request):
    return HttpResponse("OK")


def home(request):
    """Exibe a pagina inicial da aplicacao."""

    context = get_operational_home_context()
    return render(request, "core/home.html", context)


def summary_detail(request, card):
    """Exibe os lancamentos que compoem um card do resumo financeiro."""

    if card not in SUMMARY_CARD_LABELS:
        raise Http404("Card de resumo inexistente.")

    return render(
        request,
        "core/summary_detail.html",
        {"detail": get_summary_card_detail(card=card)},
    )
