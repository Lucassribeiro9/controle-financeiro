"""Views do app installments."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

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
                _add_validation_errors_to_form(form, exc)
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
    """Cancela um parcelamento sem apagar parcelas geradas."""

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    plan = get_object_or_404(InstallmentPlan, pk=plan_id)
    try:
        cancel_installment_plan(plan=plan)
    except ValidationError as exc:
        messages.error(request, _validation_error_message(exc))
    else:
        messages.success(request, "Parcelamento cancelado com sucesso.")

    return redirect("installments:detail", plan_id=plan.id)


def _add_validation_errors_to_form(
    form: InstallmentPlanForm,
    exc: ValidationError,
) -> None:
    """Transfere erros de validacao de model/service para o form."""

    if hasattr(exc, "message_dict"):
        for field, errors in exc.message_dict.items():
            for error in errors:
                form.add_error(field if field in form.fields else None, error)
        return

    form.add_error(None, _validation_error_message(exc))


def _validation_error_message(exc: ValidationError) -> str:
    """Converte ValidationError em texto exibivel."""

    if hasattr(exc, "messages"):
        return " ".join(exc.messages)

    return str(exc)
