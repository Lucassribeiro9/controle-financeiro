"""Fonte unica da definicao de gasto usada por insights, goals, reports, home e categorias."""

from .models import Transaction

# Gasto conta pela data da compra. Pagamento de fatura nunca e gasto, pois a
# compra no cartao ja foi contada.
SPENDING_TRANSACTION_TYPES = [
    Transaction.TransactionType.EXPENSE,
    Transaction.TransactionType.CARD_PURCHASE,
    Transaction.TransactionType.BENEFIT_PURCHASE,
]

# Status que tiram um lancamento do gasto (e da receita) efetivo.
EXCLUDED_SPENDING_STATUSES = [
    Transaction.PaymentStatus.IGNORED,
    Transaction.PaymentStatus.CANCELED,
    Transaction.PaymentStatus.FORECASTED,
]
