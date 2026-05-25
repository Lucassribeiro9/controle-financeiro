"""Views do app recurrences."""

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.forms import normalize_decimal

from .models import Recurrence
from transactions.models import Transaction


def _get_forecast_or_404(transaction_id: int) -> Transaction:
    """Retorna transacao prevista para acao do usuario."""

    return get_object_or_404(
        Transaction,
        pk=transaction_id,
        transaction_type=Transaction.TransactionType.FORECAST,
    )


def _extract_recurrence_name(description: str) -> str:
    """Extrai nome da recorrencia da descricao padrao [REC] Nome."""

    prefix = "[REC] "
    if description.startswith(prefix):
        return description[len(prefix) :]
    return description


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


@require_POST
def confirm_forecast(request: HttpRequest, transaction_id: int) -> JsonResponse:
    """Confirma previsao para virar transacao real pendente."""

    forecast = _get_forecast_or_404(transaction_id)
    recurrence_name = _extract_recurrence_name(forecast.description)
    recurrence = get_object_or_404(Recurrence, name=recurrence_name)

    forecast.transaction_type = _get_transaction_type_from_recurrence(recurrence)
    forecast.status = Transaction.PaymentStatus.PENDING
    forecast.save(update_fields=["transaction_type", "status", "updated_at"])

    return JsonResponse(
        {
            "id": forecast.id,
            "status": forecast.status,
            "transaction_type": forecast.transaction_type,
            "message": "Previsão confirmada com sucesso.",
        }
    )


@require_POST
def ignore_forecast(request: HttpRequest, transaction_id: int) -> JsonResponse:
    """Ignora previsao selecionada no mes."""

    forecast = _get_forecast_or_404(transaction_id)
    forecast.status = Transaction.PaymentStatus.IGNORED
    forecast.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {
            "id": forecast.id,
            "status": forecast.status,
            "message": "Previsão ignorada com sucesso.",
        }
    )


@require_POST
def adjust_forecast(request: HttpRequest, transaction_id: int) -> JsonResponse:
    """Ajusta valor previsto antes da confirmacao."""

    forecast = _get_forecast_or_404(transaction_id)
    amount_raw = request.POST.get("amount")

    if not amount_raw:
        return JsonResponse({"error": "Campo amount é obrigatório."}, status=400)

    try:
        new_amount = normalize_decimal(amount_raw)
    except ValueError:
        return JsonResponse({"error": "Campo amount inválido."}, status=400)

    if new_amount <= 0:
        return JsonResponse({"error": "Campo amount deve ser positivo."}, status=400)

    old_amount = forecast.amount
    forecast.amount = new_amount
    notes_line = f"[REC_ADJUST] de {old_amount} para {new_amount}"
    forecast.notes = f"{forecast.notes}\n{notes_line}".strip()
    forecast.save(update_fields=["amount", "notes", "updated_at"])

    return JsonResponse(
        {
            "id": forecast.id,
            "amount": str(forecast.amount),
            "message": "Previsão ajustada com sucesso.",
        }
    )
