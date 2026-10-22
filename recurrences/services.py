"""Regras de negócio para o app recurrences.
Regra principal: Recorrência gera transação prevista, nunca paga automaticamente. O usuário deve confirmar a transação prevista para que ela se torne uma transação real.
"""

from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from calendar import monthrange
from .models import Recurrence
from transactions.models import Transaction


def _clamp_day(year: int, month: int, day: int) -> int:
    """Retorna o dia ajustado para o número máximo de dias do mês."""

    _, max_day = monthrange(year, month)
    return min(day, max_day)


def _build_forecast_date(year: int, month: int, day: int) -> date:
    """Constrói a data de previsão ajustando o dia para o número máximo de dias do mês."""

    adjusted_day = _clamp_day(year, month, day)
    return date(year, month, adjusted_day)


def generate_monthly_recurrences_forecasts(*, year: int, month: int) -> int:
    """Gera transações previstas para as recorrências ativas no início de cada mês.

    Cada recorrência tem no máximo uma transação por mês, em qualquer status ou tipo.
    """
    created = 0
    recurrences = Recurrence.objects.filter(is_active=True)

    for recurrence in recurrences:
        forecast_date = _build_forecast_date(year, month, recurrence.expected_day)
        tx_type = Transaction.TransactionType.FORECAST
        already_exists = Transaction.objects.filter(
            recurrence=recurrence,
            date__year=year,
            date__month=month,
        ).exists()

        if already_exists:
            continue

        Transaction.objects.create(
            recurrence=recurrence,
            description=f"[REC] {recurrence.name}",
            amount=recurrence.expected_amount,
            transaction_type=tx_type,
            status=Transaction.PaymentStatus.FORECASTED,
            account=recurrence.account,
            card=recurrence.card,
            date=forecast_date,
            notes="Gerada automaticamente por recorrencia.",
        )
        created += 1

    return created


def skip_recurrence_for_month(*, recurrence_id: int, year: int, month: int) -> int:
    """Permite ao usuário pular a geração de uma transação prevista para um mês específico."""
    try:
        recurrence = Recurrence.objects.get(pk=recurrence_id)
    except Recurrence.DoesNotExist:
        raise ValidationError({"recurrence_id": "Recorrencia nao encontrada."})

    updated = Transaction.objects.filter(
        recurrence=recurrence,
        status=Transaction.PaymentStatus.FORECASTED,
        date__year=year,
        date__month=month,
    ).update(status=Transaction.PaymentStatus.IGNORED)
    return updated


def match_recurrence_with_transaction(
    *, recurrence_id: int, transaction_id: int
) -> bool:
    """Permite ao usuário associar uma transação real a uma recorrência prevista."""
    try:
        recurrence = Recurrence.objects.get(pk=recurrence_id)
        transaction = Transaction.objects.get(pk=transaction_id)
    except Recurrence.DoesNotExist:
        raise ValidationError({"recurrence_id": "Recorrencia nao encontrada."})
    except Transaction.DoesNotExist:
        raise ValidationError({"transaction_id": "Transacao nao encontrada."})

    if recurrence.account_id and transaction.account_id != recurrence.account_id:
        raise ValidationError(
            {"transaction_id": "Conta da transacao nao corresponde a recorrencia."}
        )

    if recurrence.card_id and transaction.card_id != recurrence.card_id:
        raise ValidationError(
            {"transaction_id": "Cartao da transacao nao corresponde a recorrencia."}
        )

    # marca como conciliada por anotacao textual.
    transaction.notes = (
        transaction.notes or ""
    ) + f"\n[REC_MATCH] recurrence_id={recurrence.id}"
    transaction.save(update_fields=["notes", "updated_at"])
    return True


def has_relevant_amount_difference(
    *,
    expected_amount: Decimal,
    actual_amount: Decimal,
    threshold: Decimal = Decimal("0.01"),
) -> bool:
    """Indica se a diferenca entre valor esperado e real e relevante."""

    return abs(expected_amount - actual_amount) >= threshold
