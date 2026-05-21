"""Views do app institutions."""

from django.contrib import messages
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InstitutionForm
from .models import Institution


def institution_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de instituicoes financeiras."""

    institutions = (
        Institution.objects.annotate(
            accounts_count=Count("accounts", distinct=True),
            cards_count=Count("cards", distinct=True),
        )
        .order_by("-is_active", "name")
    )

    return render(
        request,
        "institutions/list.html",
        {"institutions": institutions},
    )


def institution_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de instituicao."""

    if request.method == "POST":
        form = InstitutionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Instituicao criada com sucesso.")
            return redirect("institutions:list")
    else:
        form = InstitutionForm()

    return render(
        request,
        "institutions/form.html",
        {
            "form": form,
            "form_title": "Nova instituicao",
            "submit_label": "Salvar",
        },
    )


def institution_update_page(
    request: HttpRequest,
    institution_id: int,
) -> HttpResponse:
    """Renderiza e processa o formulario de edicao de instituicao."""

    institution = get_object_or_404(Institution, pk=institution_id)

    if request.method == "POST":
        form = InstitutionForm(request.POST, instance=institution)
        if form.is_valid():
            form.save()
            messages.success(request, "Instituicao atualizada com sucesso.")
            return redirect("institutions:list")
    else:
        form = InstitutionForm(instance=institution)

    return render(
        request,
        "institutions/form.html",
        {
            "form": form,
            "institution": institution,
            "form_title": "Editar instituicao",
            "submit_label": "Salvar alteracoes",
        },
    )
