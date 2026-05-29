"""Views do app installments."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import map_service_errors_to_view
from transactions.models import Transaction
from .forms import InstallmentPlanForm
from .models import InstallmentPlan
from .selectors import get_active_installment_plans, get_installment_plan_detail
from .services import cancel_installment_plan, create_installment_plan, get_installment_progress


def installment_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de parcelamentos ativos."""

    installment_plans = get_active_installment_plans()

    return render(
        request,
        "installments/list.html",
        {"installment_plans": installment_plans},
    )


def installment_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de parcelamento."""

    if request.method == "POST":
        form = InstallmentPlanForm(request.POST)
        if form.is_valid():
            try:
                plan = create_installment_plan(**form.cleaned_data)
            except ValidationError as exc:
                map_service_errors_to_view(request, exc, form=form)
            else:
                messages.success(request, "Parcelamento criado com sucesso.")
                return redirect("installments:detail", plan_id=plan.id)
    else:
        form = InstallmentPlanForm()

    return render(
        request,
        "installments/form.html",
        {"form": form},
    )


def installment_detail_page(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Renderiza detalhe de um parcelamento."""

    plan = get_installment_plan_detail(plan_id=plan_id)
    transactions = (
        plan.transactions.select_related("statement")
        .order_by("installment_number", "date")
    )

    return render(
        request,
        "installments/detail.html",
        {
            "plan": plan,
            "progress": get_installment_progress(plan=plan),
            "transactions": transactions,
        },
    )


def installment_cancel_page(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Confirma ou processa o cancelamento de um parcelamento."""

    plan = get_installment_plan_detail(plan_id=plan_id)

    if request.method == "POST":
        try:
            cancel_installment_plan(plan=plan)
        except ValidationError as exc:
            map_service_errors_to_view(request, exc)
        else:
            messages.success(request, "Parcelamento cancelado com sucesso.")
        return redirect("installments:detail", plan_id=plan.id)

    # GET: Mostra tela de confirmacao
    pending_transactions = plan.transactions.filter(
        status=Transaction.PaymentStatus.PENDING
    ).order_by("installment_number")

    return render(
        request,
        "installments/confirm_cancellation.html",
        {
            "plan": plan,
            "progress": get_installment_progress(plan=plan),
            "pending_transactions": pending_transactions,
        },
    )


def _validation_error_message(exc: ValidationError) -> str:
    """Converte ValidationError em texto exibivel."""

    if hasattr(exc, "messages"):
        return " ".join(exc.messages)

    return str(exc)
