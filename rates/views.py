"""Views do app rates."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AccountYieldConfigForm, ReferenceRateForm, YieldSimulationForm
from .models import AccountYieldConfig, ReferenceRate
from .selectors import get_account_yield_summary, get_latest_rates, get_rate_history
from .services import estimate_account_yield, save_reference_rate


def rates_page(request: HttpRequest) -> HttpResponse:
    """Renderiza resumo de taxas e rendimentos estimados."""

    latest_rates = get_latest_rates()
    rate_history = get_rate_history(ReferenceRate.RateType.CDI)[:10]
    yield_summary = get_account_yield_summary(months=12)

    return render(
        request,
        "rates/list.html",
        {
            "latest_rates": latest_rates,
            "latest_cdi": latest_rates.get(ReferenceRate.RateType.CDI),
            "rate_history": rate_history,
            "yield_summary": yield_summary,
            "months": 12,
        },
    )


def reference_rate_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa cadastro manual de CDI."""

    if request.method == "POST":
        form = ReferenceRateForm(request.POST)
        if form.is_valid():
            try:
                save_reference_rate(**form.cleaned_data)
            except ValidationError as exc:
                _add_validation_errors_to_form(form, exc)
            else:
                messages.success(request, "CDI cadastrado com sucesso.")
                return redirect("rates:list")
    else:
        form = ReferenceRateForm(initial={"date": timezone.localdate()})

    return render(
        request,
        "rates/rate_form.html",
        {"form": form},
    )


def yield_config_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa cadastro de configuracao de rendimento."""

    if request.method == "POST":
        form = AccountYieldConfigForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, "Configuracao de rendimento criada com sucesso.")
            return redirect("rates:yield-config-edit", config_id=config.id)
    else:
        form = AccountYieldConfigForm()

    return render(
        request,
        "rates/yield_config_form.html",
        {
            "form": form,
            "form_title": "Nova configuracao de rendimento",
            "submit_label": "Salvar",
        },
    )


def yield_config_update_page(request: HttpRequest, config_id: int) -> HttpResponse:
    """Renderiza e processa edicao de configuracao de rendimento."""

    config = get_object_or_404(
        AccountYieldConfig.objects.select_related("account"),
        pk=config_id,
    )

    if request.method == "POST":
        form = AccountYieldConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save()
            messages.success(request, "Configuracao de rendimento atualizada com sucesso.")
            return redirect("rates:yield-config-edit", config_id=config.id)
    else:
        form = AccountYieldConfigForm(instance=config)

    return render(
        request,
        "rates/yield_config_form.html",
        {
            "form": form,
            "config": config,
            "form_title": "Editar configuracao de rendimento",
            "submit_label": "Salvar alteracoes",
        },
    )


def yield_simulation_page(request: HttpRequest) -> HttpResponse:
    """Renderiza simulador de rendimento por conta."""

    estimate = None
    if request.method == "POST":
        form = YieldSimulationForm(request.POST)
        if form.is_valid():
            try:
                estimate = estimate_account_yield(
                    account=form.cleaned_data["account"],
                    amount=form.cleaned_data["amount"],
                    months=form.cleaned_data["months"],
                )
            except ValidationError as exc:
                _add_validation_errors_to_form(form, exc)
    else:
        form = YieldSimulationForm(initial={"months": 12})

    return render(
        request,
        "rates/simulation.html",
        {
            "form": form,
            "estimate": estimate,
        },
    )


def _add_validation_errors_to_form(form, exc: ValidationError) -> None:
    """Transfere erros de validacao para o form."""

    if hasattr(exc, "message_dict"):
        for field, errors in exc.message_dict.items():
            for error in errors:
                form.add_error(field if field in form.fields else None, error)
        return

    for error in exc.messages:
        form.add_error(None, error)
