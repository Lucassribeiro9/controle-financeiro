"""Consultas e agregacoes para cartoes."""

from decimal import Decimal

from django.db.models import Sum

from transactions.models import Transaction

from .models import CardStatement


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

    return (
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


def get_statement_summary(statement):
    """Calcula o resumo de valores da fatura para a tela de detalhe."""

    purchase_total = get_statement_purchase_total(statement)
    closed_amount = statement.closed_amount or purchase_total
    remaining_amount = max(closed_amount - statement.paid_amount, Decimal("0.00"))

    return {
        "expected_amount": purchase_total,
        "closed_amount": closed_amount,
        "paid_amount": statement.paid_amount,
        "remaining_amount": remaining_amount,
        "status": statement.status,
        "is_fully_paid": closed_amount > Decimal("0.00") and remaining_amount == Decimal("0.00"),
    }
