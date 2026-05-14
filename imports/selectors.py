"""Seletores para as funcionalidades de importacao."""

from .models import ImportedTransaction


def get_imported_transactions_for_review(*, status=None):
    """Lista transacoes importadas que precisam de revisao."""

    queryset = ImportedTransaction.objects.select_related(
        "suggested_account",
        "suggested_category",
        "confirmed_transaction",
    )

    if status:
        return queryset.filter(status=status)

    return queryset.filter(
        status__in=[
            ImportedTransaction.Status.PENDING,
            ImportedTransaction.Status.DUPLICATE,
        ]
    )
