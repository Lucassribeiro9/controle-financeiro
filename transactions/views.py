"""Views do app transactions."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.utils import map_service_errors_to_view
from .forms import TransactionForm, TransferForm
from .models import Transaction
from .selectors import (
    get_transactions_by_status,
    get_transactions_by_type,
    get_transactions_for_period,
    get_transfers_for_period,
)
from .services import (
    create_transaction_by_payment_method,
    create_transfer,
)


def _get_period_from_request(request: HttpRequest) -> tuple[int, int]:
    """Extrai ano e mes da query string ou usa o mes atual."""

    today = timezone.localdate()
    year = int(request.GET.get("year") or today.year)
    month = int(request.GET.get("month") or today.month)
    return year, month


def transaction_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de lancamentos financeiros."""

    year, month = _get_period_from_request(request)
    status = request.GET.get("status")
    transaction_type = request.GET.get("transaction_type")

    if status:
        transactions = get_transactions_by_status(status=status)
    elif transaction_type:
        transactions = get_transactions_by_type(transaction_type=transaction_type)
    else:
        transactions = get_transactions_for_period(year=year, month=month)

    return render(
        request,
        "transactions/list.html",
        {
            "year": year,
            "month": month,
            "status": status,
            "transaction_type": transaction_type,
            "status_choices": Transaction.PaymentStatus.choices,
            "transaction_type_choices": Transaction.TransactionType.choices,
            "transactions": transactions,
        },
    )


def transaction_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de lancamento."""

    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            try:
                if form.cleaned_data["payment_method"] == "transfer":
                    create_transfer(
                        description=form.cleaned_data["description"],
                        amount=form.cleaned_data["amount"],
                        from_account=form.cleaned_data["from_account"],
                        destination_account=form.cleaned_data["destination_account"],
                        date=form.cleaned_data["date"],
                        notes=form.cleaned_data["notes"],
                    )
                    messages.success(request, "Transferência criada com sucesso.")
                    return redirect("transactions:transfers")

                transaction = create_transaction_by_payment_method(
                    payment_method=form.cleaned_data["payment_method"],
                    description=form.cleaned_data["description"],
                    amount=form.cleaned_data["amount"],
                    transaction_type=form.cleaned_data["transaction_type"],
                    date=form.cleaned_data["date"],
                    account=form.cleaned_data["account"],
                    category=form.cleaned_data["category"],
                    card=form.cleaned_data["card"],
                    status=form.cleaned_data["status"],
                    notes=form.cleaned_data["notes"],
                )
            except ValidationError as exc:
                map_service_errors_to_view(request, exc, form=form)
            else:
                messages.success(request, "Lançamento criado com sucesso.")
                return redirect("transactions:detail", transaction_id=transaction.id)
    else:
        form = TransactionForm(
            initial={
                "date": timezone.localdate(),
                "status": Transaction.PaymentStatus.PENDING,
            }
        )

    return render(
        request,
        "transactions/form.html",
        {"form": form},
    )


def transaction_detail_page(
    request: HttpRequest,
    transaction_id: int,
) -> HttpResponse:
    """Renderiza o detalhe de um lancamento financeiro."""

    transaction = get_object_or_404(
        Transaction.objects.select_related("account", "category", "card", "statement"),
        pk=transaction_id,
    )
    return render(
        request,
        "transactions/detail.html",
        {"transaction": transaction},
    )


def transfer_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de transferencias entre contas."""

    year, month = _get_period_from_request(request)
    transfers = get_transfers_for_period(year=year, month=month)

    return render(
        request,
        "transactions/transfers.html",
        {
            "year": year,
            "month": month,
            "transfers": transfers,
        },
    )


def transfer_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de transferencia."""

    if request.method == "POST":
        form = TransferForm(request.POST)
        if form.is_valid():
            try:
                create_transfer(**form.cleaned_data)
            except ValidationError as exc:
                map_service_errors_to_view(request, exc, form=form)
            else:
                messages.success(request, "Transferência criada com sucesso.")
                return redirect("transactions:transfers")
    else:
        form = TransferForm(initial={"date": timezone.localdate()})

    return render(
        request,
        "transactions/transfer_form.html",
        {"form": form},
    )
