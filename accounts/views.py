"""Views do app accounts."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FinancialAccountForm
from .models import FinancialAccount
from .selectors import get_account_summary


def account_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de contas financeiras agrupadas por moeda."""

    account_summary = get_account_summary()

    return render(
        request,
        "accounts/list.html",
        {"account_summary": account_summary},
    )


def account_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de conta."""

    if request.method == "POST":
        form = FinancialAccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            messages.success(request, "Conta criada com sucesso.")
            return redirect("accounts:detail", account_id=account.id)
    else:
        form = FinancialAccountForm()

    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "form_title": "Nova conta",
            "submit_label": "Salvar",
        },
    )


def account_update_page(request: HttpRequest, account_id: int) -> HttpResponse:
    """Renderiza e processa o formulario de edicao de conta."""

    account = get_object_or_404(
        FinancialAccount.objects.select_related("institution"),
        pk=account_id,
    )

    if request.method == "POST":
        form = FinancialAccountForm(request.POST, instance=account)
        if form.is_valid():
            account = form.save()
            messages.success(request, "Conta atualizada com sucesso.")
            return redirect("accounts:detail", account_id=account.id)
    else:
        form = FinancialAccountForm(instance=account)

    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "account": account,
            "form_title": "Editar conta",
            "submit_label": "Salvar alterações",
        },
    )


def account_detail_page(request: HttpRequest, account_id: int) -> HttpResponse:
    """Renderiza o detalhe de uma conta financeira."""

    account = get_object_or_404(
        FinancialAccount.objects.select_related("institution"),
        pk=account_id,
    )
    return render(
        request,
        "accounts/detail.html",
        {"account": account},
    )
