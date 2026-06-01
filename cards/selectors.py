"""Consultas e agregacoes para cartoes."""

from decimal import Decimal

from django.db.models import Sum

from transactions.models import Transaction

from .models import CardStatement

MONEY_QUANT = Decimal("0.01")


def _money(value):
    """Normaliza valores monetarios para a precisao dos campos Decimal."""

    return (value or Decimal("0.00")).quantize(MONEY_QUANT)


def get_card_limits(card):
    """Calcula limite cadastrado, usado e disponivel de um cartao de credito."""

    credit_limit = card.credit_limit or Decimal("0.00")
    used_limit = (
        Transaction.objects.filter(
            card=card,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            statement__isnull=False,
        )
        .exclude(
            status__in=[
                Transaction.PaymentStatus.CANCELED,
                Transaction.PaymentStatus.IGNORED,
            ]
        )
        .exclude(statement__status=CardStatement.StatementStatus.PAID)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    return {
        "credit_limit": credit_limit,
        "used_limit": used_limit,
        "available_limit": credit_limit - used_limit,
    }


def get_statement_purchase_total(statement):
    """Calcula o total ativo das compras vinculadas a uma fatura."""

    total = (
        statement.transactions.filter(
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
        )
        .exclude(
            status__in=[
                Transaction.PaymentStatus.CANCELED,
                Transaction.PaymentStatus.IGNORED,
            ]
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    return _money(total)


def get_statement_summary(statement):
    """Calcula o resumo de valores da fatura para a tela de detalhe."""

    purchase_total = get_statement_purchase_total(statement)
    persisted_closed_amount = _money(statement.closed_amount)
    is_open_statement = statement.status in (
        CardStatement.StatementStatus.OPEN,
        CardStatement.StatementStatus.FORECASTED,
    )
    closed_amount = (
        persisted_closed_amount
        if is_open_statement
        else persisted_closed_amount or purchase_total
    )
    paid_amount = _money(statement.paid_amount)
    remaining_base = purchase_total if is_open_statement else closed_amount
    remaining_amount = max(remaining_base - paid_amount, Decimal("0.00"))

    return {
        "expected_amount": purchase_total,
        "closed_amount": closed_amount,
        "paid_amount": paid_amount,
        "remaining_amount": remaining_amount,
        "status": statement.status,
        "is_fully_paid": closed_amount > Decimal("0.00") and remaining_amount == Decimal("0.00"),
    }
