"""Selectors para consultas de previsoes recorrentes."""

from transactions.models import Transaction


def get_recurring_forecasts_for_period(
    *, year: int, month: int, statuses: list[str] | None = None
):
    """Lista previsoes recorrentes vinculadas a uma recorrencia no periodo.

    Criterio unico de "previsao recorrente" (decisao #218): transacao do
    tipo FORECAST com `recurrence` vinculada. Previsoes orfas (recorrencia
    apagada ou legadas sem vinculo) nao entram aqui, entao nao aparecem na
    tela de previsoes nem no resumo da home (#206, #218).
    """

    queryset = Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.FORECAST,
        date__year=year,
        date__month=month,
        recurrence__isnull=False,
    ).select_related("recurrence")

    if statuses is not None:
        queryset = queryset.filter(status__in=statuses)

    return queryset.order_by("date", "description")
