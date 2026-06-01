"""Regras de negocio para transacoes e transferencias."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.services import (
    get_or_create_card_statement,
    refresh_statement_amounts,
)
from installments.services import create_installment_plan_from_purchase

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

    _apply_account_delta(account_id=transaction.account_id, delta=balance_delta)


def _apply_account_delta(*, account_id, delta):
    """Aplica ajuste em conta financeira com lock pessimista."""

    if not account_id or delta == Decimal("0.00"):
        return

    account = FinancialAccount.objects.select_for_update().get(pk=account_id)
    account.balance += delta
    account.save(update_fields=["balance", "updated_at"])


def _get_benefit_card_purchase_amount(transaction):
    """Retorna impacto em saldo proprio de beneficio, quando aplicavel."""

    if (
        transaction.transaction_type == Transaction.TransactionType.CARD_PURCHASE
        and transaction.card_id
        and transaction.card.card_type == Card.CardType.BENEFIT
    ):
        return transaction.amount

    return Decimal("0.00")


def _apply_benefit_card_delta(*, card_id, delta):
    """Aplica ajuste no saldo proprio do cartao de beneficio."""

    if not card_id or delta == Decimal("0.00"):
        return

    card = Card.objects.select_for_update().get(pk=card_id)
    if card.card_type != Card.CardType.BENEFIT:
        raise ValidationError("Benefício exige cartão de benefício.")

    card.balance += delta
    if card.balance < Decimal("0.00"):
        raise ValidationError("Saldo insuficiente no cartão de benefício.")

    card.full_clean()
    card.save(update_fields=["balance", "updated_at"])


def _resolve_card_purchase_statement(*, transaction_type, card, transaction_date):
    """Resolve fatura conforme tipo de cartao usado na compra."""

    if transaction_type != Transaction.TransactionType.CARD_PURCHASE or card is None:
        return None

    if card.card_type == Card.CardType.CREDIT:
        return get_or_create_card_statement(card=card, transaction_date=transaction_date)

    return None


def _ensure_statement_can_change(statement):
    """Bloqueia alteracao de compras em faturas finais."""

    if statement is None:
        return

    statement.refresh_from_db()
    if statement.status == CardStatement.StatementStatus.CANCELED:
        raise ValidationError("Fatura cancelada nao permite alteracao de compras.")
    if statement.status == CardStatement.StatementStatus.PAID:
        raise ValidationError("Fatura paga nao permite alteracao de compras.")


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


def _create_benefit_purchase(
    *,
    description,
    amount,
    date,
    card,
    category=None,
    status=Transaction.PaymentStatus.PENDING,
    notes="",
):
    """Cria compra em beneficio debitando saldo e transacao atomicamente."""

    if amount <= Decimal("0.00"):
        raise ValidationError("Valor deve ser maior que zero.")

    with db_transaction.atomic():
        card = Card.objects.select_for_update().get(pk=card.pk)
        if card.card_type != Card.CardType.BENEFIT:
            raise ValidationError("Benefício exige cartão de benefício.")

        if card.balance < amount:
            raise ValidationError("Saldo insuficiente no cartão de benefício.")

        card.balance -= amount
        card.full_clean()
        card.save(update_fields=["balance", "updated_at"])

        transaction = Transaction(
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
        transaction.full_clean()
        transaction.save()

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
    total_installments=None,
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

        if total_installments and total_installments > 1:
            return create_installment_plan_from_purchase(
                description=description,
                total_amount=amount,
                total_installments=total_installments,
                purchase_date=date,
                card=card,
                category=category,
            )

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

        return _create_benefit_purchase(
            description=description,
            amount=amount,
            date=date,
            card=card,
            category=category,
            status=status,
            notes=notes,
        )

    raise ValidationError("Forma de pagamento inválida.")


def update_transaction(
    *,
    transaction_id,
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
    """Atualiza um lancamento e recalcula impactos financeiros."""

    with db_transaction.atomic():
        transaction = (
            Transaction.objects.select_for_update()
            .select_related("account", "card", "statement")
            .get(pk=transaction_id)
        )

        previous_account_id = transaction.account_id
        previous_balance_delta = _get_balance_delta(transaction)
        previous_benefit_card_id = transaction.card_id
        previous_benefit_amount = _get_benefit_card_purchase_amount(transaction)
        previous_statement = transaction.statement
        new_statement = _resolve_card_purchase_statement(
            transaction_type=transaction_type,
            card=card,
            transaction_date=date,
        )
        affected_statements = [
            statement
            for statement in (previous_statement, new_statement)
            if statement is not None
        ]
        for statement in affected_statements:
            _ensure_statement_can_change(statement)

        if transaction_type != Transaction.TransactionType.CARD_PURCHASE:
            card = None
            new_statement = None

        if card and card.card_type in (Card.CardType.CREDIT, Card.CardType.BENEFIT):
            account = None

        _apply_account_delta(
            account_id=previous_account_id,
            delta=previous_balance_delta * Decimal("-1"),
        )
        _apply_benefit_card_delta(
            card_id=previous_benefit_card_id,
            delta=previous_benefit_amount,
        )

        transaction.description = description
        transaction.amount = amount
        transaction.transaction_type = transaction_type
        transaction.date = date
        transaction.account = account
        transaction.category = category
        transaction.card = card
        transaction.statement = new_statement
        transaction.status = status
        transaction.notes = notes
        transaction.full_clean()
        transaction.save()

        _apply_balance_delta(transaction=transaction)
        _apply_benefit_card_delta(
            card_id=transaction.card_id,
            delta=_get_benefit_card_purchase_amount(transaction) * Decimal("-1"),
        )

        refreshed_statement_ids = set()
        for statement in affected_statements:
            if statement.id in refreshed_statement_ids:
                continue
            refresh_statement_amounts(statement=statement)
            refreshed_statement_ids.add(statement.id)

    return transaction


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
