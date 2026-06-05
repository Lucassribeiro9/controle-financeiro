"""Regras de negocio para importacoes."""

import hashlib
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from categories.models import Category
from transactions.models import Transaction
from transactions.services import create_transaction

from .models import ImportedTransaction


REVIEWABLE_IMPORT_STATUSES = [
    ImportedTransaction.Status.PENDING,
    ImportedTransaction.Status.DUPLICATE,
]
@dataclass(frozen=True)
class BulkImportActionResult:
    """Resume o resultado de uma acao em lote na revisao."""

    processed: int = 0
    skipped: int = 0


def _normalize_duplicate_description(description: str) -> str:
    return " ".join(description.strip().lower().split())


def build_import_hash(
    *,
    source_type,
    date,
    amount,
    normalized_description,
    external_id="",
) -> str:
    """Gera uma chave estavel para identificar uma linha importada."""

    raw_value = "|".join(
        [
            source_type,
            date.isoformat(),
            str(amount),
            normalized_description.strip().lower(),
            external_id.strip(),
        ]
    )
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def suggest_category(description):
    """Sugere uma categoria com base na descricao importada."""

    description = description.lower()

    if "supermercado" in description or "mercado" in description:
        return Category.objects.filter(name__icontains="aliment").first()

    if "uber" in description or "99" in description:
        return Category.objects.filter(name__icontains="transporte").first()

    return None


def detect_duplicate_import(*, imported_transaction):
    """Detecta duplicidade entre importacoes ja registradas."""

    if imported_transaction.external_id:
        return ImportedTransaction.objects.filter(
            source_type=imported_transaction.source_type,
            external_id=imported_transaction.external_id,
        ).exists()

    if imported_transaction.import_hash:
        return ImportedTransaction.objects.filter(
            import_hash=imported_transaction.import_hash,
        ).exists()

    return False


def detect_duplicate_transaction(*, imported_transaction):
    """Detecta se a linha importada parece uma transacao real ja cadastrada."""

    if not imported_transaction.suggested_account_id:
        return False

    candidates = Transaction.objects.filter(
        date=imported_transaction.date,
        amount=imported_transaction.amount,
        account=imported_transaction.suggested_account,
    ).only("description")
    expected_description = _normalize_duplicate_description(
        imported_transaction.normalized_description
    )

    return any(
        _normalize_duplicate_description(candidate.description) == expected_description
        for candidate in candidates
    )


def stage_imported_transactions(*, file_name, source_type, rows, suggested_account=None):
    """Salva linhas importadas como pendencias para revisao do usuario."""

    imported = []

    with db_transaction.atomic():
        for row in rows:
            import_hash = build_import_hash(
                source_type=source_type,
                date=row.date,
                amount=row.amount,
                normalized_description=row.normalized_description,
                external_id=row.external_id,
            )

            imported_transaction = ImportedTransaction(
                source_file_name=file_name,
                source_type=source_type,
                raw_description=row.raw_description,
                normalized_description=row.normalized_description,
                amount=row.amount,
                date=row.date,
                suggested_account=suggested_account,
                suggested_category=suggest_category(row.normalized_description),
                suggested_transaction_type=row.suggested_transaction_type,
                external_id=row.external_id,
                import_hash=import_hash,
                status=ImportedTransaction.Status.PENDING,
            )

            if detect_duplicate_import(imported_transaction=imported_transaction):
                imported_transaction.status = ImportedTransaction.Status.DUPLICATE
            elif detect_duplicate_transaction(imported_transaction=imported_transaction):
                imported_transaction.status = ImportedTransaction.Status.DUPLICATE

            imported_transaction.full_clean()
            imported_transaction.save()
            imported.append(imported_transaction)

    return imported


def confirm_imported_transaction(
    *,
    imported_transaction,
    account,
    category=None,
    transaction_type=None,
    description=None,
    amount=None,
    date=None,
):
    """Confirma uma importacao e cria a transacao real correspondente."""

    if imported_transaction.status == ImportedTransaction.Status.CONFIRMED:
        return imported_transaction.confirmed_transaction

    transaction_type = transaction_type or imported_transaction.suggested_transaction_type
    description = description or imported_transaction.normalized_description
    amount = imported_transaction.amount if amount is None else amount
    date = date or imported_transaction.date

    if not transaction_type:
        raise ValueError("Informe o tipo da transacao antes de confirmar a importacao.")

    with db_transaction.atomic():
        transaction = create_transaction(
            description=description,
            amount=amount,
            date=date,
            transaction_type=transaction_type,
            account=account,
            category=category,
            status=Transaction.PaymentStatus.PAID,
            notes=f"Importado de {imported_transaction.source_file_name}",
        )

        imported_transaction.normalized_description = description
        imported_transaction.amount = amount
        imported_transaction.date = date
        imported_transaction.confirmed_transaction = transaction
        imported_transaction.status = ImportedTransaction.Status.CONFIRMED
        imported_transaction.review_error = ""
        imported_transaction.full_clean()
        imported_transaction.save(
            update_fields=[
                "normalized_description",
                "amount",
                "date",
                "confirmed_transaction",
                "status",
                "review_error",
                "updated_at",
            ]
        )

    return transaction


def discard_imported_transaction(*, imported_transaction):
    """Descarta uma importacao pendente sem criar transacao real."""

    imported_transaction.status = ImportedTransaction.Status.DISCARDED
    imported_transaction.confirmed_transaction = None
    imported_transaction.review_error = ""
    imported_transaction.full_clean()
    imported_transaction.save(
        update_fields=["status", "confirmed_transaction", "review_error", "updated_at"]
    )
    return imported_transaction


def _get_reviewable_imports(*, selected_ids):
    """Retorna somente itens explicitamente selecionados e revisaveis."""

    return ImportedTransaction.objects.filter(
        pk__in=selected_ids,
        status__in=REVIEWABLE_IMPORT_STATUSES,
    ).select_related("suggested_account", "suggested_category")


def apply_account_to_imports(*, selected_ids, account):
    """Aplica conta aos itens importados selecionados."""

    queryset = _get_reviewable_imports(selected_ids=selected_ids)
    processed = queryset.update(suggested_account=account, review_error="")
    return BulkImportActionResult(processed=processed)


def apply_category_to_imports(*, selected_ids, category):
    """Aplica categoria aos itens importados selecionados."""

    queryset = _get_reviewable_imports(selected_ids=selected_ids)
    processed = queryset.update(suggested_category=category, review_error="")
    return BulkImportActionResult(processed=processed)


def confirm_imported_transactions_partially(*, selected_ids):
    """Confirma itens validos e persiste erro nos invalidos sem abortar o lote."""

    processed = 0
    skipped = 0

    with db_transaction.atomic():
        queryset = _get_reviewable_imports(selected_ids=selected_ids).select_for_update()
        for imported_transaction in queryset:
            if not imported_transaction.suggested_account_id:
                imported_transaction.review_error = "Informe uma conta para confirmar."
                imported_transaction.save(update_fields=["review_error", "updated_at"])
                skipped += 1
                continue

            if not imported_transaction.suggested_transaction_type:
                imported_transaction.review_error = "Informe o tipo antes de confirmar."
                imported_transaction.save(update_fields=["review_error", "updated_at"])
                skipped += 1
                continue

            try:
                confirm_imported_transaction(
                    imported_transaction=imported_transaction,
                    account=imported_transaction.suggested_account,
                    category=imported_transaction.suggested_category,
                    transaction_type=imported_transaction.suggested_transaction_type,
                )
            except (ValueError, ValidationError) as exc:
                imported_transaction.review_error = str(exc)
                imported_transaction.save(update_fields=["review_error", "updated_at"])
                skipped += 1
            else:
                processed += 1

    return BulkImportActionResult(processed=processed, skipped=skipped)


def discard_imported_transactions(*, selected_ids):
    """Descarta itens importados selecionados."""

    processed = 0
    for imported_transaction in _get_reviewable_imports(selected_ids=selected_ids):
        discard_imported_transaction(imported_transaction=imported_transaction)
        processed += 1

    return BulkImportActionResult(processed=processed)
