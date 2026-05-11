"""Regras de negocio para transacoes e transferencias."""

from django.db import transaction as db_transaction

from accounts.models import FinancialAccount

from .models import Transaction, Transfer


def create_transaction(
    *,
    description,
    amount,
    transaction_type,
    date,
    account=None,
    category=None,
    card=None,
    status=Transaction.PaymentStatus.PENDING,
    notes="",
):
    """Cria uma transacao validada e aplica efeito simples no saldo."""

    transaction = Transaction(
        description=description,
        amount=amount,
        transaction_type=transaction_type,
        status=status,
        account=account,
        category=category,
        card=card,
        date=date,
        notes=notes,
    )
    transaction.full_clean()

    with db_transaction.atomic():
        if transaction.account_id:
            transaction.account = FinancialAccount.objects.select_for_update().get(
                pk=transaction.account_id
            )

        transaction.save()

        if transaction.account_id and transaction.transaction_type == Transaction.TransactionType.INCOME:
            transaction.account.balance += transaction.amount
            transaction.account.save(update_fields=["balance", "updated_at"])

        if transaction.account_id and transaction.transaction_type in (
            Transaction.TransactionType.EXPENSE,
            Transaction.TransactionType.STATEMENT_PAYMENT,
        ):
            transaction.account.balance -= transaction.amount
            transaction.account.save(update_fields=["balance", "updated_at"])

    return transaction


def create_transfer(
    *,
    description,
    amount,
    from_account,
    destination_account,
    date,
    notes="",
):
    """Cria uma transferencia validada e move saldo entre contas."""

    transfer = Transfer(
        description=description,
        amount=amount,
        from_account=from_account,
        destination_account=destination_account,
        date=date,
        notes=notes,
    )
    transfer.full_clean()

    with db_transaction.atomic():
        source_account = FinancialAccount.objects.select_for_update().get(pk=from_account.pk)
        target_account = FinancialAccount.objects.select_for_update().get(pk=destination_account.pk)

        transfer.from_account = source_account
        transfer.destination_account = target_account
        transfer.save()

        source_account.balance -= transfer.amount
        target_account.balance += transfer.amount

        source_account.save(update_fields=["balance", "updated_at"])
        target_account.save(update_fields=["balance", "updated_at"])

    return transfer

def mark_transaction_as_paid(transaction_id):
    """Marca uma transação como paga sem reaplicar impacto no saldo."""
    with db_transaction.atomic():
        transaction = Transaction.objects.select_for_update().get(pk=transaction_id)

        if transaction.status == Transaction.PaymentStatus.PAID:
            return transaction  # Já está pago, não faz nada

        transaction.status = Transaction.PaymentStatus.PAID
        transaction.save(update_fields=["status", "updated_at"])

    return transaction
