"""Views do app imports."""

from django.contrib import messages
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from accounts.models import FinancialAccount
from categories.models import Category
from core.forms import normalize_decimal
from core.forms import parse_br_date
from transactions.models import Transaction

from .importers import get_importer_for_source_type
from .models import ImportedTransaction
from .selectors import get_imported_transactions_for_review
from .selectors import get_import_review_filter_options
from .services import (
    confirm_imported_transaction,
    discard_imported_transaction,
    stage_imported_transactions,
)


REVIEW_NEXT_VALUE = "review-page"


def _review_filters_from_request(request: HttpRequest) -> dict:
    """Extrai filtros da revisao sem incluir valores vazios."""

    return {
        key: value
        for key, value in {
            "status": request.GET.get("status"),
            "source_file_name": request.GET.get("source_file_name"),
            "source_type": request.GET.get("source_type"),
            "start_date": request.GET.get("start_date"),
            "end_date": request.GET.get("end_date"),
        }.items()
        if value
    }


def _serialize_imported_transaction(imported_transaction: ImportedTransaction) -> dict:
    """Serializa uma transacao importada para respostas JSON."""

    return {
        "id": imported_transaction.id,
        "source_file_name": imported_transaction.source_file_name,
        "source_type": imported_transaction.source_type,
        "raw_description": imported_transaction.raw_description,
        "normalized_description": imported_transaction.normalized_description,
        "amount": str(imported_transaction.amount),
        "date": imported_transaction.date.isoformat(),
        "status": imported_transaction.status,
        "suggested_account_id": imported_transaction.suggested_account_id,
        "suggested_category_id": imported_transaction.suggested_category_id,
        "suggested_transaction_type": imported_transaction.suggested_transaction_type,
        "confirmed_transaction_id": imported_transaction.confirmed_transaction_id,
        "external_id": imported_transaction.external_id,
    }


def _stage_import_from_request(request: HttpRequest):
    """Processa o arquivo enviado e cria pendencias para revisao."""
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        raise ValueError("Campo file é obrigatório.")

    source_type = request.POST.get("source_type", ImportedTransaction.SourceType.CSV)

    suggested_account = None
    account_id = request.POST.get("account_id")
    if account_id:
        suggested_account = get_object_or_404(FinancialAccount, pk=account_id)

    try:
        importer = get_importer_for_source_type(source_type)
        rows = importer.parse(uploaded_file)
        imported_transactions = stage_imported_transactions(
            file_name=uploaded_file.name,
            source_type=source_type,
            rows=rows,
            suggested_account=suggested_account,
        )
    except ValueError:
        raise

    return imported_transactions


def _should_redirect_to_review(request: HttpRequest) -> bool:
    """Identifica envios vindos das telas HTML."""

    return request.POST.get("next") == REVIEW_NEXT_VALUE


def _redirect_to_review(request: HttpRequest):
    """Redireciona para a tela mantendo filtros quando vierem no form."""

    query_string = request.POST.get("review_query", "")
    redirect_url = redirect("imports:review-page")
    if query_string:
        redirect_url["Location"] = f"{redirect_url['Location']}?{query_string}"
    return redirect_url


def _parse_decimal(value):
    """Converte valor monetario informado no formulario."""

    if value in (None, ""):
        return None

    try:
        return normalize_decimal(value)
    except ValueError as exc:
        raise ValueError("Valor informado é inválido.") from exc


def _parse_transaction_date(value):
    """Converte data informada no formulario."""

    if value in (None, ""):
        return None

    try:
        return parse_br_date(value)
    except ValueError as exc:
        raise ValueError("Data informada é inválida.")
    except Exception as exc:
        raise ValueError("Data informada é inválida.") from exc


@require_POST
def upload_import(request: HttpRequest) -> JsonResponse:
    """Recebe arquivo suportado e cria transacoes importadas para revisao."""

    try:
        imported_transactions = _stage_import_from_request(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "count": len(imported_transactions),
            "results": [
                _serialize_imported_transaction(imported_transaction)
                for imported_transaction in imported_transactions
            ],
        },
        status=201,
    )


@require_GET
def review_imports(request: HttpRequest) -> JsonResponse:
    """Lista transacoes importadas para revisao."""

    queryset = get_imported_transactions_for_review(
        **_review_filters_from_request(request)
    )

    results = [_serialize_imported_transaction(item) for item in queryset]
    return JsonResponse({"count": len(results), "results": results})


@require_POST
def confirm_import(request: HttpRequest, imported_transaction_id: int) -> JsonResponse:
    """Confirma uma transacao importada e cria a transacao real."""

    imported_transaction = get_object_or_404(
        ImportedTransaction,
        pk=imported_transaction_id,
    )

    account_id = request.POST.get("account_id") or imported_transaction.suggested_account_id
    if not account_id:
        if _should_redirect_to_review(request):
            messages.error(request, "Informe uma conta para confirmar.")
            return _redirect_to_review(request)
        return JsonResponse({"error": "Informe account_id para confirmar."}, status=400)

    account = get_object_or_404(FinancialAccount, pk=account_id)

    category = None
    category_id = request.POST.get("category_id") or imported_transaction.suggested_category_id
    if category_id:
        category = get_object_or_404(Category, pk=category_id)

    transaction_type = request.POST.get("transaction_type") or None
    description = request.POST.get("description") or None

    try:
        amount = _parse_decimal(request.POST.get("amount"))
        transaction_date = _parse_transaction_date(request.POST.get("date"))
    except ValueError as exc:
        if _should_redirect_to_review(request):
            messages.error(request, str(exc))
            return _redirect_to_review(request)
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        transaction = confirm_imported_transaction(
            imported_transaction=imported_transaction,
            account=account,
            category=category,
            transaction_type=transaction_type,
            description=description,
            amount=amount,
            date=transaction_date,
        )
    except ValueError as exc:
        if _should_redirect_to_review(request):
            messages.error(request, str(exc))
            return _redirect_to_review(request)
        return JsonResponse({"error": str(exc)}, status=400)

    if _should_redirect_to_review(request):
        messages.success(request, "Importação confirmada.")
        return _redirect_to_review(request)

    return JsonResponse(
        {
            "id": imported_transaction.id,
            "status": ImportedTransaction.Status.CONFIRMED,
            "confirmed_transaction_id": transaction.id,
        }
    )


@require_POST
def discard_import(request: HttpRequest, imported_transaction_id: int) -> JsonResponse:
    """Descarta uma transacao importada sem criar transacao real."""

    imported_transaction = get_object_or_404(
        ImportedTransaction,
        pk=imported_transaction_id,
    )
    discarded = discard_imported_transaction(imported_transaction=imported_transaction)

    if _should_redirect_to_review(request):
        messages.success(request, "Importação descartada.")
        return _redirect_to_review(request)

    return JsonResponse(
        {
            "id": discarded.id,
            "status": discarded.status,
        }
    )


@require_http_methods(["GET", "POST"])
def upload_import_page(request: HttpRequest):
    """Renderiza a pagina de upload de arquivos para importacao."""

    accounts = FinancialAccount.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        try:
            imported_transactions = _stage_import_from_request(request)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"{len(imported_transactions)} transação(ões) enviada(s) para revisão.",
            )
            return redirect("imports:review-page")

    return render(
        request,
        "imports/upload.html",
        {
            "accounts": accounts,
            "source_types": ImportedTransaction.SourceType.choices,
        },
    )


@require_GET
def review_imports_page(request: HttpRequest):
    """Renderiza a pagina de revisao de transacoes importadas."""

    imported_transactions = get_imported_transactions_for_review(
        **_review_filters_from_request(request)
    )
    filter_options = get_import_review_filter_options()
    return render(
        request,
        "imports/review.html",
        {
            "imported_transactions": imported_transactions,
            "filter_options": filter_options,
            "active_filters": request.GET,
            "review_query_string": request.GET.urlencode(),
            "accounts": FinancialAccount.objects.filter(is_active=True).order_by("name"),
            "categories": Category.objects.order_by("name"),
            "transaction_types": [
                choice
                for choice in Transaction.TransactionType.choices
                if choice[0]
                in [
                    Transaction.TransactionType.INCOME,
                    Transaction.TransactionType.EXPENSE,
                ]
            ],
            "review_next_value": REVIEW_NEXT_VALUE,
        },
    )


@require_POST
def bulk_review_imports(request: HttpRequest):
    """Confirma ou descarta importacoes selecionadas na tela de revisao."""

    selected_ids = request.POST.getlist("selected_imports")
    action = request.POST.get("bulk_action")

    if not selected_ids:
        messages.error(request, "Selecione ao menos uma importação.")
        return _redirect_to_review(request)

    queryset = ImportedTransaction.objects.filter(
        pk__in=selected_ids,
        status__in=[
            ImportedTransaction.Status.PENDING,
            ImportedTransaction.Status.DUPLICATE,
        ],
    ).select_related("suggested_account", "suggested_category")

    processed = 0
    skipped = 0

    if action == "discard":
        for imported_transaction in queryset:
            discard_imported_transaction(imported_transaction=imported_transaction)
            processed += 1
        messages.success(request, f"{processed} importação(ões) descartada(s).")
        return _redirect_to_review(request)

    if action == "confirm":
        for imported_transaction in queryset:
            if not imported_transaction.suggested_account_id:
                skipped += 1
                continue

            try:
                confirm_imported_transaction(
                    imported_transaction=imported_transaction,
                    account=imported_transaction.suggested_account,
                    category=imported_transaction.suggested_category,
                    transaction_type=imported_transaction.suggested_transaction_type,
                )
            except ValueError:
                skipped += 1
            else:
                processed += 1

        if processed:
            messages.success(request, f"{processed} importação(ões) confirmada(s).")
        if skipped:
            messages.error(
                request,
                f"{skipped} importação(ões) precisam de conta e tipo antes de confirmar.",
            )
        return _redirect_to_review(request)

    messages.error(request, "Ação em lote inválida.")
    return _redirect_to_review(request)
