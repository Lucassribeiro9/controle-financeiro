"""Views do app cards."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import map_service_errors_to_view
from core.forms import normalize_decimal
from .forms import CardForm, StatementPaymentForm
from .models import Card, CardStatement
from .selectors import get_card_limits
from .services import close_statement, pay_statement, update_statement_status
from decimal import Decimal, InvalidOperation


def card_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de cartoes."""

    cards = list(
        Card.objects.select_related("institution", "payment_account")
        .order_by("-is_active", "institution__name", "name")
    )
    for card in cards:
        card.limit_summary = get_card_limits(card) if card.card_type == Card.CardType.CREDIT else None

    return render(
        request,
        "cards/list.html",
        {"cards": cards},
    )


def card_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de cartao."""

    if request.method == "POST":
        form = CardForm(request.POST)
        if form.is_valid():
            card = form.save()
            messages.success(request, "Cartão criado com sucesso.")
            return redirect("cards:list")
    else:
        form = CardForm()

    return render(
        request,
        "cards/form.html",
        {
            "form": form,
            "form_title": "Novo cartão",
            "submit_label": "Salvar",
        },
    )


def card_update_page(request: HttpRequest, card_id: int) -> HttpResponse:
    """Renderiza e processa o formulario de edicao de cartao."""

    card = get_object_or_404(
        Card.objects.select_related("institution", "payment_account"),
        pk=card_id,
    )

    if request.method == "POST":
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, "Cartão atualizado com sucesso.")
            return redirect("cards:list")
    else:
        form = CardForm(instance=card)

    return render(
        request,
        "cards/form.html",
        {
            "form": form,
            "card": card,
            "form_title": "Editar cartão",
            "submit_label": "Salvar alterações",
        },
    )


def statement_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de faturas."""

    statements = (
        CardStatement.objects.select_related(
            "card",
            "card__institution",
            "payment_account",
        )
        .order_by("-year", "-month", "card__name")
    )
    statements = [
        update_statement_status(statement=statement)
        for statement in statements
    ]

    return render(
        request,
        "cards/statements.html",
        {"statements": statements},
    )


def statement_detail_page(request: HttpRequest, statement_id: int) -> HttpResponse:
    """Renderiza o detalhe de uma fatura e permite fechamento via POST."""

    statement = _get_statement(statement_id=statement_id)

    if request.method == "POST":
        try:
            close_statement(statement=statement)
        except ValidationError as exc:
            messages.error(request, _validation_error_message(exc))
        else:
            messages.success(request, "Fatura fechada com sucesso.")

        return redirect("cards:statement-detail", statement_id=statement.id)

    statement = update_statement_status(statement=statement)
    payment_form = StatementPaymentForm(statement=statement)

    return render(
        request,
        "cards/statement_detail.html",
        {
            "statement": statement,
            "payment_form": payment_form,
            "transactions": statement.transactions.order_by("-date", "-created_at"),
        },
    )


def pay_statement_page(request: HttpRequest, statement_id: int) -> HttpResponse:
    """Processa ou confirma pagamento de fatura."""

    statement = _get_statement(statement_id=statement_id)
    payment_account = statement.payment_account or statement.card.payment_account

    if not payment_account:
        messages.error(request, "Fatura exige conta de pagamento.")
        return redirect("cards:statement-detail", statement_id=statement.id)

    if request.method == "POST":
        form = StatementPaymentForm(request.POST, statement=statement)
        if form.is_valid():
            try:
                pay_statement(
                    statement=statement,
                    amount=form.cleaned_data["amount"],
                )
            except ValidationError as exc:
                map_service_errors_to_view(request, exc, form=form)
            else:
                messages.success(request, "Fatura paga com sucesso.")
                return redirect("cards:statement-detail", statement_id=statement.id)
    else:
        # GET: Mostra tela de confirmacao
        amount_str = request.GET.get("amount")
        initial_amount = None
        if amount_str:
            try:
                # normalize_decimal ja lida com formatos pt-BR e ISO
                initial_amount = normalize_decimal(amount_str)
            except (ValueError, InvalidOperation):
                pass
        
        if initial_amount is None:
            initial_amount = statement.closed_amount - statement.paid_amount
            
        form = StatementPaymentForm(initial={"amount": initial_amount}, statement=statement)

    # Dados para a confirmacao
    current_balance = payment_account.balance
    
    # Se o form for valido (POST) ou tiver valor inicial (GET), calcula projecao
    payment_amount = Decimal("0.00")
    if form.is_bound and form.is_valid():
        payment_amount = form.cleaned_data.get("amount") or (statement.closed_amount - statement.paid_amount)
    else:
        payment_amount = form.initial.get("amount") or (statement.closed_amount - statement.paid_amount)
    
    projected_balance = current_balance - payment_amount

    return render(
        request,
        "cards/confirm_payment.html",
        {
            "statement": statement,
            "form": form,
            "payment_account": payment_account,
            "current_balance": current_balance,
            "payment_amount": payment_amount,
            "projected_balance": projected_balance,
        },
    )


def _get_statement(*, statement_id: int) -> CardStatement:
    """Busca fatura com relacionamentos principais carregados."""

    return get_object_or_404(
        CardStatement.objects.select_related(
            "card",
            "card__institution",
            "payment_account",
            "card__payment_account",
        ),
        pk=statement_id,
    )


def _validation_error_message(exc: ValidationError) -> str:
    """Converte ValidationError em mensagem exibivel."""

    if hasattr(exc, "message_dict"):
        messages_list = []
        for field_errors in exc.message_dict.values():
            messages_list.extend(field_errors)
        return " ".join(messages_list)

    return " ".join(exc.messages)
