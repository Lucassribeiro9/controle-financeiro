"""Seletores para as funcionalidades de importacao."""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils.dateparse import parse_date

from .models import ImportedTransaction


IMPORT_REVIEW_PAGE_SIZE = 25

TAB_PENDING = "pendentes"
TAB_NO_CATEGORY = "sem-categoria"
TAB_NO_ACCOUNT = "sem-conta"
TAB_DUPLICATE = "duplicadas"
TAB_TREATED = "tratadas"
DEFAULT_REVIEW_TAB = TAB_PENDING

IMPORT_REVIEW_TABS = (
    (TAB_PENDING, "Pendentes"),
    (TAB_NO_CATEGORY, "Sem categoria"),
    (TAB_NO_ACCOUNT, "Sem conta"),
    (TAB_DUPLICATE, "Duplicadas"),
    (TAB_TREATED, "Tratadas"),
)

_OPEN_STATUSES = (
    ImportedTransaction.Status.PENDING,
    ImportedTransaction.Status.DUPLICATE,
)
_TREATED_STATUSES = (
    ImportedTransaction.Status.CONFIRMED,
    ImportedTransaction.Status.DISCARDED,
)


def normalize_review_tab(tab):
    """Devolve a aba valida; valores desconhecidos caem em Pendentes."""

    if tab in dict(IMPORT_REVIEW_TABS):
        return tab
    return DEFAULT_REVIEW_TAB


def _tab_q(tab):
    """Condicao de cada aba sobre status e sugestoes."""

    open_rows = Q(status__in=_OPEN_STATUSES)
    if tab == TAB_NO_CATEGORY:
        return open_rows & Q(suggested_category__isnull=True)
    if tab == TAB_NO_ACCOUNT:
        return open_rows & Q(suggested_account__isnull=True)
    if tab == TAB_DUPLICATE:
        return Q(status=ImportedTransaction.Status.DUPLICATE)
    if tab == TAB_TREATED:
        return Q(status__in=_TREATED_STATUSES)
    return open_rows


def get_imported_transactions_for_review(
    *,
    tab=None,
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
    """Lista transacoes importadas da aba ativa (padrao: Pendentes)."""

    queryset = _filtered_imports(
        status=status,
        source_file_name=source_file_name,
        source_type=source_type,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        q=q,
    )
    return queryset.filter(_tab_q(normalize_review_tab(tab))).select_related(
        "suggested_account",
        "suggested_category",
        "confirmed_transaction",
    )


def get_import_review_tab_counts(**filters):
    """Conta as cinco abas numa consulta so, respeitando os filtros (menos a aba)."""

    filters.pop("tab", None)
    aliases = {tab: f"tab_{index}" for index, (tab, _label) in enumerate(IMPORT_REVIEW_TABS)}
    totals = _filtered_imports(**filters).aggregate(
        **{alias: Count("pk", filter=_tab_q(tab)) for tab, alias in aliases.items()}
    )
    return {tab: totals[alias] for tab, alias in aliases.items()}


def _filtered_imports(
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
    """Aplica os filtros comuns as abas e aos contadores."""

    queryset = ImportedTransaction.objects.all()

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


def get_category_history(keys):
    """Mapeia (descricao original, tipo) para a categoria do historico confirmado.

    Usa a confirmacao mais recente cuja categoria existe e esta ativa. Uma
    unica consulta, sem escrita.
    """

    keys = set(keys)
    if not keys:
        return {}

    confirmed = (
        ImportedTransaction.objects.filter(
            status=ImportedTransaction.Status.CONFIRMED,
            raw_description__in={description for description, _type in keys},
            confirmed_transaction__category__isnull=False,
            confirmed_transaction__category__is_active=True,
        )
        .select_related("confirmed_transaction__category")
        .order_by("-confirmed_transaction_id")
    )

    history = {}
    for imported in confirmed:
        transaction = imported.confirmed_transaction
        key = (imported.raw_description, transaction.transaction_type)
        if key in keys and key not in history:
            history[key] = transaction.category
    return history


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
