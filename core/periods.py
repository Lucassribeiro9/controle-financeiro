"""Periodo (ano/mes) recebido pela query string."""

from django.http import HttpRequest
from django.utils import timezone

MIN_YEAR = 2000
MAX_YEAR = 2100


def _parse_int(raw: str | None) -> int | None:
    """Converte o valor para inteiro; vazio/espacos viram None, invalido levanta ValueError."""

    value = (raw or "").strip()
    if not value:
        return None
    return int(value)


def get_period_from_request(request: HttpRequest) -> tuple[int, int]:
    """Extrai (ano, mes) de `?year=&month=` ou usa o mes atual.

    Valor ausente, vazio, nao numerico, mes fora de 1..12 ou ano fora de
    MIN_YEAR..MAX_YEAR faz o periodo inteiro cair no mes atual, sem erro.
    """

    today = timezone.localdate()
    try:
        year = _parse_int(request.GET.get("year"))
        month = _parse_int(request.GET.get("month"))
    except ValueError:
        return today.year, today.month

    year = today.year if year is None else year
    month = today.month if month is None else month
    if not MIN_YEAR <= year <= MAX_YEAR or not 1 <= month <= 12:
        return today.year, today.month
    return year, month
