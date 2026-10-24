"""Views do app accounts."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import map_service_errors_to_view
from transactions.services import adjust_account_balance

from .forms import AccountBalanceAdjustmentForm, FinancialAccountForm
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
    recent_transactions = account.transactions.order_by("-date", "-created_at")[:10]
    return render(
        request,
        "accounts/detail.html",
        {"account": account, "recent_transactions": recent_transactions},
    )


def account_adjust_balance_page(request: HttpRequest, account_id: int) -> HttpResponse:
    """Renderiza e processa o ajuste do saldo da conta ao saldo real."""

    account = get_object_or_404(
        FinancialAccount.objects.select_related("institution"),
        pk=account_id,
    )

    if request.method == "POST":
        form = AccountBalanceAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                adjustment = adjust_account_balance(
                    account=account,
                    real_balance=form.cleaned_data["real_balance"],
                    notes=form.cleaned_data["notes"],
                )
            except ValidationError as exc:
                map_service_errors_to_view(request, exc, form=form)
            else:
                if adjustment is None:
                    messages.info(request, "O saldo informado é igual ao atual; nada foi alterado.")
                else:
                    messages.success(request, "Saldo ajustado com sucesso.")
                return redirect("accounts:detail", account_id=account.id)
    else:
        form = AccountBalanceAdjustmentForm(initial={"real_balance": account.balance})

    return render(
        request,
        "accounts/adjust_balance.html",
        {"form": form, "account": account},
    )
