"""Regras de negocio para importacoes."""

import hashlib

from django.db import transaction as db_transaction

from categories.models import Category
from transactions.models import Transaction
from transactions.services import create_transaction

from .models import ImportedTransaction


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

    return Transaction.objects.filter(
        date=imported_transaction.date,
        amount=imported_transaction.amount,
        description__icontains=imported_transaction.normalized_description[:20],
    ).exists()


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
        imported_transaction.full_clean()
        imported_transaction.save(
            update_fields=[
                "normalized_description",
                "amount",
                "date",
                "confirmed_transaction",
                "status",
                "updated_at",
            ]
        )

    return transaction


def discard_imported_transaction(*, imported_transaction):
    """Descarta uma importacao pendente sem criar transacao real."""

    imported_transaction.status = ImportedTransaction.Status.DISCARDED
    imported_transaction.confirmed_transaction = None
    imported_transaction.full_clean()
    imported_transaction.save(
        update_fields=["status", "confirmed_transaction", "updated_at"]
    )
    return imported_transaction
