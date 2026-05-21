"""Filtros de formatacao monetaria para templates."""

from decimal import Decimal
from decimal import InvalidOperation
from decimal import ROUND_HALF_UP

from django import template


register = template.Library()


@register.filter
def brl(value):
    """Formata valores como moeda brasileira."""

    if value in (None, ""):
        value = Decimal("0.00")

    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return value

    sign = "-" if amount < Decimal("0.00") else ""
    absolute = abs(amount)
    integer_part, decimal_part = f"{absolute:.2f}".split(".")

    grouped = []
    while integer_part:
        grouped.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]

    return f"{sign}R$ {'.'.join(grouped)},{decimal_part}"
