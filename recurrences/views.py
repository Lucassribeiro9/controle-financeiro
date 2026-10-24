"""Views do app recurrences."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.auth import api_login_required
from core.forms import normalize_decimal

from .models import Recurrence
from transactions.models import Transaction


def _get_transaction_type_from_recurrence(recurrence: Recurrence) -> str:
    """Converte tipo de recorrencia para tipo real de transacao."""

    if recurrence.recurrence_type == Recurrence.RecurrenceType.INCOME:
        return Transaction.TransactionType.INCOME
    return Transaction.TransactionType.EXPENSE


def _get_period_from_request(request: HttpRequest) -> tuple[int, int]:
    """Extrai ano e mes da query string ou usa o mes atual."""

    today = timezone.localdate()
    year = int(request.GET.get("year") or today.year)
    month = int(request.GET.get("month") or today.month)
    return year, month


def _get_forecasts_for_period(*, year: int, month: int):
    """Lista previsoes recorrentes de um periodo."""

    return Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.FORECAST,
        date__year=year,
        date__month=month,
    ).order_by("date", "description")


@api_login_required
@require_GET
def monthly_forecasts(request: HttpRequest, year: int, month: int) -> JsonResponse:
    """Lista previsoes do mes para conferencia do usuario."""

    forecasts = _get_forecasts_for_period(year=year, month=month)

    payload = [
        {
            "id": tx.id,
            "description": tx.description,
            "amount": str(tx.amount),
            "status": tx.status,
            "date": tx.date.isoformat(),
            "account_id": tx.account_id,
            "card_id": tx.card_id,
        }
        for tx in forecasts
    ]
    return JsonResponse({"count": len(payload), "results": payload})


@require_GET
def forecasts_page(request: HttpRequest, year: int, month: int):
    """Renderiza a pagina de previsoes recorrentes do mes."""

    forecasts = _get_forecasts_for_period(year=year, month=month)
    return render(
        request,
        "recurrences/forecasts.html",
        {
            "year": year,
            "month": month,
            "forecasts": forecasts,
        },
    )


@require_GET
def forecasts_filter_page(request: HttpRequest):
    """Renderiza previsoes recorrentes usando periodo informado por filtro."""

    year, month = _get_period_from_request(request)
    return forecasts_page(request, year=year, month=month)


def _redirect_to_forecasts_month(forecast: Transaction) -> HttpResponse:
    """Volta para a tela de previsoes do mes da previsao."""

    return redirect(
        "recurrences:forecasts-page", year=forecast.date.year, month=forecast.date.month
    )


def _lock_forecast_or_404(transaction_id: int) -> Transaction:
    """Le a previsao com lock; aceita a ja processada para manter idempotencia.

    Deve rodar dentro de `transaction.atomic`. Transacao que nunca foi previsao
    (sem recorrencia de origem) responde 404.
    """

    transaction_obj = get_object_or_404(
        Transaction.objects.select_for_update().select_related("recurrence"),
        pk=transaction_id,
    )
    is_forecast = transaction_obj.transaction_type == Transaction.TransactionType.FORECAST
    if not is_forecast and transaction_obj.recurrence_id is None:
        raise Http404("Transacao nao e uma previsao recorrente.")
    return transaction_obj


@require_POST
def confirm_forecast(request: HttpRequest, transaction_id: int) -> HttpResponse:
    """Confirma previsao para virar transacao real pendente."""

    with transaction.atomic():
        forecast = _lock_forecast_or_404(transaction_id)
        if forecast.transaction_type != Transaction.TransactionType.FORECAST:
            messages.info(request, "Esta previsão já foi confirmada.")
            return _redirect_to_forecasts_month(forecast)

        recurrence = forecast.recurrence
        if recurrence is None:
            raise Http404("Previsao sem recorrencia de origem.")

        forecast.transaction_type = _get_transaction_type_from_recurrence(recurrence)
        forecast.status = Transaction.PaymentStatus.PENDING
        forecast.save(update_fields=["transaction_type", "status", "updated_at"])

    messages.success(request, "Previsão confirmada com sucesso.")
    return _redirect_to_forecasts_month(forecast)


@require_POST
def ignore_forecast(request: HttpRequest, transaction_id: int) -> HttpResponse:
    """Ignora previsao selecionada no mes."""

    with transaction.atomic():
        forecast = _lock_forecast_or_404(transaction_id)
        if forecast.transaction_type != Transaction.TransactionType.FORECAST:
            messages.error(request, "Esta previsão já foi confirmada e não pode ser ignorada.")
            return _redirect_to_forecasts_month(forecast)
        if forecast.status == Transaction.PaymentStatus.IGNORED:
            messages.info(request, "Esta previsão já foi ignorada.")
            return _redirect_to_forecasts_month(forecast)

        forecast.status = Transaction.PaymentStatus.IGNORED
        forecast.save(update_fields=["status", "updated_at"])

    messages.success(request, "Previsão ignorada com sucesso.")
    return _redirect_to_forecasts_month(forecast)


@require_POST
def adjust_forecast(request: HttpRequest, transaction_id: int) -> HttpResponse:
    """Ajusta valor previsto antes da confirmacao."""

    amount_raw = request.POST.get("amount")

    with transaction.atomic():
        forecast = _lock_forecast_or_404(transaction_id)
        if forecast.transaction_type != Transaction.TransactionType.FORECAST:
            messages.error(request, "Esta previsão já foi confirmada e não pode ser ajustada.")
            return _redirect_to_forecasts_month(forecast)

        if not amount_raw:
            messages.error(request, "Informe o novo valor da previsão.")
            return _redirect_to_forecasts_month(forecast)

        try:
            new_amount = normalize_decimal(amount_raw)
            if not new_amount.is_finite():
                raise ValueError("Valor nao finito.")
        except ValueError:
            messages.error(request, "Valor inválido. Use o formato 0,00.")
            return _redirect_to_forecasts_month(forecast)

        if new_amount <= 0:
            messages.error(request, "O novo valor deve ser maior que zero.")
            return _redirect_to_forecasts_month(forecast)

        old_amount = forecast.amount
        if new_amount == old_amount:
            messages.info(request, "O valor informado é igual ao valor atual.")
            return _redirect_to_forecasts_month(forecast)

        forecast.amount = new_amount
        notes_line = f"[REC_ADJUST] de {old_amount} para {new_amount}"
        forecast.notes = f"{forecast.notes}\n{notes_line}".strip()
        try:
            forecast.full_clean()
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return _redirect_to_forecasts_month(forecast)
        forecast.save(update_fields=["amount", "notes", "updated_at"])

    messages.success(request, "Previsão ajustada com sucesso.")
    return _redirect_to_forecasts_month(forecast)
