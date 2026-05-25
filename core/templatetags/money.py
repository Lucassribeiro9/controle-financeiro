"""Filtros de formatacao financeira para templates."""

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from decimal import ROUND_HALF_UP

from django import template
from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_datetime


register = template.Library()

STATUS_BADGE_VARIANTS = {
    "active": "success",
    "achieved": "success",
    "approved": "success",
    "confirmed": "success",
    "completed": "success",
    "paid": "success",
    "pending": "warning",
    "partially_paid": "warning",
    "partial": "warning",
    "duplicate": "warning",
    "open": "info",
    "forecasted": "info",
    "forecast": "info",
    "on_track": "info",
    "late": "danger",
    "missed": "danger",
    "at_risk": "danger",
    "canceled": "neutral",
    "cancelled": "neutral",
    "discarded": "neutral",
    "ignored": "neutral",
    "inactive": "neutral",
    "silenced": "neutral",
}


@register.filter
def brl(value):
    """Formata valores como moeda brasileira."""

    return currency(value, "BRL")


@register.filter
def currency(value, currency_code="BRL"):
    """Formata valores monetários com moeda e separadores pt-BR."""

    currency_code = (currency_code or "BRL").upper()
    symbols = {
        "BRL": "R$",
        "USD": "US$",
    }
    prefix = symbols.get(currency_code, currency_code)
    amount = _decimal(value)
    if amount is None:
        return value

    return f"{_sign(amount)}{prefix} {_format_decimal(abs(amount), 2)}"


@register.filter
def decimal_ptbr(value, decimal_places=2):
    """Formata decimal sem símbolo, para exibição ou valor de input."""

    amount = _decimal(value)
    if amount is None:
        return value

    places = int(decimal_places)
    return f"{_sign(amount)}{_format_decimal(abs(amount), places)}"


@register.filter
def date_br(value):
    """Formata datas como dd/mm/aaaa."""

    if value in (None, ""):
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    parsed_datetime = parse_datetime(str(value))
    if parsed_datetime is not None:
        return parsed_datetime.strftime("%d/%m/%Y %H:%M")

    parsed_date = parse_date(str(value))
    if parsed_date is not None:
        return parsed_date.strftime("%d/%m/%Y")

    return value


@register.filter
def percentage(value, decimal_places=2):
    """Formata percentuais já armazenados em escala 100."""

    amount = _decimal(value)
    if amount is None:
        return value
    return f"{_format_decimal(amount, int(decimal_places))}%"


@register.filter
def annual_rate(value, decimal_places=2):
    """Formata taxa anual decimal como percentual ao ano."""

    amount = _decimal(value)
    if amount is None:
        return value
    return f"{_format_decimal(amount * Decimal('100'), int(decimal_places))}% a.a."


@register.filter
def status_badge_class(value):
    """Retorna a classe visual apropriada para um status."""

    normalized = _normalize_status_key(value)
    variant = STATUS_BADGE_VARIANTS.get(normalized, "neutral")
    return f"badge badge-{variant}"


@register.filter
def active_badge_class(value):
    """Retorna a classe visual para estados ativo/inativo."""

    return "badge badge-success" if value else "badge badge-neutral"


def _decimal(value):
    if value in (None, ""):
        value = Decimal("0.00")

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _sign(value):
    return "-" if value < Decimal("0.00") else ""


def _format_decimal(value, decimal_places):
    quantizer = Decimal("1").scaleb(-decimal_places)
    amount = value.quantize(quantizer, rounding=ROUND_HALF_UP)
    if decimal_places == 0:
        integer_part = f"{amount:.0f}"
        grouped = []
        while integer_part:
            grouped.insert(0, integer_part[-3:])
            integer_part = integer_part[:-3]
        return ".".join(grouped)

    integer_part, decimal_part = f"{amount:.{decimal_places}f}".split(".")
    grouped = []
    while integer_part:
        grouped.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]

    return f"{'.'.join(grouped)},{decimal_part}"


def _normalize_status_key(value):
    if value in (None, ""):
        return ""

    return str(value).strip().lower().replace(" ", "_")
