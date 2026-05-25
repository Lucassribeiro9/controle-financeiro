"""Seletores para as funcionalidades de importacao."""

from django.utils.dateparse import parse_date

from .models import ImportedTransaction


def get_imported_transactions_for_review(
    *,
    status=None,
    source_file_name=None,
    source_type=None,
    start_date=None,
    end_date=None,
):
    """Lista transacoes importadas que precisam de revisao."""

    queryset = ImportedTransaction.objects.select_related(
        "suggested_account",
        "suggested_category",
        "confirmed_transaction",
    )

    if status:
        queryset = queryset.filter(status=status)
    else:
        queryset = queryset.filter(status__in=[
            ImportedTransaction.Status.PENDING,
            ImportedTransaction.Status.DUPLICATE,
        ])

    if source_file_name:
        queryset = queryset.filter(source_file_name=source_file_name)

    if source_type:
        queryset = queryset.filter(source_type=source_type)

    parsed_start_date = _parse_filter_date(start_date)
    if parsed_start_date:
        queryset = queryset.filter(date__gte=parsed_start_date)

    parsed_end_date = _parse_filter_date(end_date)
    if parsed_end_date:
        queryset = queryset.filter(date__lte=parsed_end_date)

    return queryset


def get_import_review_filter_options():
    """Retorna opcoes disponiveis para filtros da tela de revisao."""

    return {
        "source_files": (
            ImportedTransaction.objects.order_by("source_file_name")
            .values_list("source_file_name", flat=True)
            .distinct()
        ),
        "source_types": ImportedTransaction.SourceType.choices,
        "statuses": ImportedTransaction.Status.choices,
    }


def _parse_filter_date(value):
    if not value:
        return None

    return parse_date(value)
