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
