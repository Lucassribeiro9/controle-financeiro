"""Regras de negocio para transacoes e transferencias."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from accounts.models import FinancialAccount
from cards.models import Card
from cards.services import (
    credit_benefit_card_balance,
    debit_benefit_card_balance,
    get_or_create_card_statement,
)

from .models import Transaction, Transfer


BALANCE_IMPACT_STATUS = Transaction.PaymentStatus.PAID
BALANCE_IMPACT_BY_TYPE = {
    Transaction.TransactionType.INCOME: Decimal("1"),
    Transaction.TransactionType.EXPENSE: Decimal("-1"),
    Transaction.TransactionType.STATEMENT_PAYMENT: Decimal("-1"),
}


def _get_balance_delta(transaction):
    """Retorna o impacto em saldo conforme tipo e status da transacao."""

    if transaction.status != BALANCE_IMPACT_STATUS:
        return Decimal("0.00")

    multiplier = BALANCE_IMPACT_BY_TYPE.get(transaction.transaction_type, Decimal("0"))
    return transaction.amount * multiplier


def _apply_balance_delta(*, transaction):
    balance_delta = _get_balance_delta(transaction)
    if not transaction.account_id or balance_delta == Decimal("0.00"):
        return

    transaction.account = FinancialAccount.objects.select_for_update().get(
        pk=transaction.account_id
    )
    transaction.account.balance += balance_delta
    transaction.account.save(update_fields=["balance", "updated_at"])


def create_transaction(
    *,
    description,
    amount,
    transaction_type,
    date,
    account=None,
    category=None,
    card=None,
    statement=None,
    status=Transaction.PaymentStatus.PENDING,
    notes="",
):
    """Cria uma transacao validada e aplica saldo apenas se estiver paga."""

    transaction = Transaction(
        description=description,
        amount=amount,
        transaction_type=transaction_type,
        status=status,
        account=account,
        category=category,
        card=card,
        statement=statement,
        date=date,
        notes=notes,
    )
    transaction.full_clean()

    with db_transaction.atomic():
        transaction.save()
        _apply_balance_delta(transaction=transaction)

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


def create_transaction_by_payment_method(
    *,
    payment_method,
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
    """Cria o lancamento correto a partir da forma de pagamento informada."""

    if payment_method == "transfer":
        raise ValidationError("Transferência deve ser criada pelo fluxo de transferências.")

    if payment_method in {"debit", "cash"}:
        return create_transaction(
            description=description,
            amount=amount,
            transaction_type=transaction_type,
            date=date,
            account=account,
            category=category,
            card=card,
            status=status,
            notes=notes,
        )

    if payment_method == "credit":
        if card is None:
            raise ValidationError("Compra no cartão exige cartão vinculado.")
        if card.card_type != Card.CardType.CREDIT:
            raise ValidationError("Crédito exige cartão de crédito.")

        statement = get_or_create_card_statement(card=card, transaction_date=date)
        return create_transaction(
            description=description,
            amount=amount,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            date=date,
            card=card,
            statement=statement,
            category=category,
            status=status,
            notes=notes,
        )

    if payment_method == "benefit":
        if card is None:
            raise ValidationError("Benefício exige cartão vinculado.")
        if card.card_type != Card.CardType.BENEFIT:
            raise ValidationError("Benefício exige cartão de benefício.")

        debit_benefit_card_balance(card=card, amount=amount)
        return create_transaction(
            description=description,
            amount=amount,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            date=date,
            card=card,
            category=category,
            statement=None,
            status=status,
            notes=notes,
        )

    raise ValidationError("Forma de pagamento inválida.")


def mark_transaction_as_paid(transaction_id):
    """Marca uma transacao como paga e aplica impacto em saldo uma unica vez."""

    with db_transaction.atomic():
        transaction = Transaction.objects.select_for_update().get(pk=transaction_id)

        if transaction.status == Transaction.PaymentStatus.PAID:
            return transaction

        transaction.status = Transaction.PaymentStatus.PAID
        transaction.full_clean()
        _apply_balance_delta(transaction=transaction)
        transaction.save(update_fields=["status", "updated_at"])

    return transaction
