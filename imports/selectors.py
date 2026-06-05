"""Seletores para as funcionalidades de importacao."""

from django.core.paginator import Paginator
from django.utils.dateparse import parse_date

from .models import ImportedTransaction


IMPORT_REVIEW_PAGE_SIZE = 25


def get_imported_transactions_for_review(
    *,
    status=None,
    source_file_name=None,
    source_type=None,
    start_date=None,
    end_date=None,
    account_id=None,
    category_id=None,
    transaction_type=None,
    q=None,
):
    """Lista transacoes importadas que precisam de revisao."""

    queryset = ImportedTransaction.objects.select_related(
        "suggested_account",
        "suggested_category",
        "confirmed_transaction",
    )

    if status:
        queryset = queryset.filter(status=status)

    if source_file_name:
        queryset = queryset.filter(source_file_name=source_file_name)

    if source_type:
        queryset = queryset.filter(source_type=source_type)

    if account_id:
        queryset = queryset.filter(suggested_account_id=account_id)

    if category_id:
        queryset = queryset.filter(suggested_category_id=category_id)

    if transaction_type:
        queryset = queryset.filter(suggested_transaction_type=transaction_type)

    if q:
        queryset = queryset.filter(normalized_description__icontains=q.strip())

    parsed_start_date = _parse_filter_date(start_date)
    if parsed_start_date:
        queryset = queryset.filter(date__gte=parsed_start_date)

    parsed_end_date = _parse_filter_date(end_date)
    if parsed_end_date:
        queryset = queryset.filter(date__lte=parsed_end_date)

    return queryset


def paginate_imported_transactions_for_review(
    *,
    queryset,
    page_number=None,
    per_page=IMPORT_REVIEW_PAGE_SIZE,
):
    """Pagina a lista de importacoes em revisao."""

    paginator = Paginator(queryset, per_page)
    return paginator.get_page(page_number)


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
