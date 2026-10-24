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

# Tipos que tem fluxo proprio (fatura, recorrencia, ajuste na conta) e por isso
# nao passam pela edicao generica (spec 013, #224).
GENERIC_EDIT_BLOCKED_TYPES = {
    Transaction.TransactionType.STATEMENT_PAYMENT: (
        "Pagamento de fatura não pode ser editado por aqui; ele segue o fluxo da fatura."
    ),
    Transaction.TransactionType.FORECAST: (
        "Previsão não pode ser editada por aqui; confirme ou ajuste pela recorrência."
    ),
    Transaction.TransactionType.ADJUSTMENT_IN: (
        "Ajuste de saldo não pode ser editado; registre um novo ajuste na conta."
    ),
    Transaction.TransactionType.ADJUSTMENT_OUT: (
        "Ajuste de saldo não pode ser editado; registre um novo ajuste na conta."
    ),
}
