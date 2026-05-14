"""Views do app imports."""

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from accounts.models import FinancialAccount
from categories.models import Category

from .importers import get_importer_for_source_type
from .models import ImportedTransaction
from .selectors import get_imported_transactions_for_review
from .services import (
    confirm_imported_transaction,
    discard_imported_transaction,
    stage_imported_transactions,
)


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


@require_POST
def upload_import(request: HttpRequest) -> JsonResponse:
    """Recebe um arquivo suportado e cria transacoes importadas para revisao."""

    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return JsonResponse({"error": "Campo file e obrigatorio."}, status=400)

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

    status = request.GET.get("status")
    queryset = get_imported_transactions_for_review(status=status)

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
        return JsonResponse({"error": "Informe account_id para confirmar."}, status=400)

    account = get_object_or_404(FinancialAccount, pk=account_id)

    category = None
    category_id = request.POST.get("category_id") or imported_transaction.suggested_category_id
    if category_id:
        category = get_object_or_404(Category, pk=category_id)

    transaction_type = request.POST.get("transaction_type") or None

    try:
        transaction = confirm_imported_transaction(
            imported_transaction=imported_transaction,
            account=account,
            category=category,
            transaction_type=transaction_type,
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

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

    return JsonResponse(
        {
            "id": discarded.id,
            "status": discarded.status,
        }
    )
