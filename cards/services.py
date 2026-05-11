"""Regras de negocio para cartoes e faturas."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.db.models import Sum

from transactions.models import Transaction

from .models import Card, CardStatement


def _next_month(*, year, month):
    """Retorna o proximo mes preservando virada de ano."""

    if month == 12:
        return year + 1, 1

    return year, month + 1


def _safe_date(*, year, month, day):
    """Cria uma data usando o ultimo dia valido quando necessario."""

    last_day = monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def get_or_create_card_statement(*, card, transaction_date):
    """Identifica ou cria a fatura do cartao correspondente a data da transacao."""

    card = Card.objects.get(pk=card.pk)
    if card.card_type != Card.CardType.CREDIT:
        raise ValidationError("Apenas cartoes de credito possuem faturas.")

    statement_year = transaction_date.year
    statement_month = transaction_date.month

    if transaction_date.day > card.statement_closing_day:
        statement_year, statement_month = _next_month(
            year=statement_year,
            month=statement_month,
        )

    due_year = statement_year
    due_month = statement_month
    if card.statement_due_day <= card.statement_closing_day:
        due_year, due_month = _next_month(year=due_year, month=due_month)

    statement, _created = CardStatement.objects.get_or_create(
        card=card,
        year=statement_year,
        month=statement_month,
        defaults={
            "closing_date": _safe_date(
                year=statement_year,
                month=statement_month,
                day=card.statement_closing_day,
            ),
            "due_date": _safe_date(
                year=due_year,
                month=due_month,
                day=card.statement_due_day,
            ),
            "payment_account": card.payment_account,
        },
    )

    return statement


def close_statement(*, statement):
    """Fecha a fatura calculando o valor fechado sem alterar saldo."""

    with db_transaction.atomic():
        statement = CardStatement.objects.select_for_update().get(pk=statement.pk)

        if statement.status == CardStatement.StatementStatus.CANCELED:
            raise ValidationError("Fatura cancelada nao pode ser fechada.")

        if statement.status in (
            CardStatement.StatementStatus.PENDING,
            CardStatement.StatementStatus.PARTIALLY_PAID,
            CardStatement.StatementStatus.PAID,
        ):
            raise ValidationError("Fatura ja foi fechada.")

        total = (
            statement.transactions.filter(
                transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            )
            .exclude(
                status__in=[
                    Transaction.PaymentStatus.CANCELED,
                    Transaction.PaymentStatus.IGNORED,
                ]
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        statement.closed_amount = total
        statement.status = CardStatement.StatementStatus.PENDING
        statement.full_clean()
        statement.save(update_fields=["closed_amount", "status", "updated_at"])

    return statement


def pay_statement(*, statement, amount=None):
    """Paga total ou parcialmente uma fatura e reduz a conta de pagamento."""

    with db_transaction.atomic():
        statement = CardStatement.objects.select_for_update().get(pk=statement.pk)

        if statement.status == CardStatement.StatementStatus.CANCELED:
            raise ValidationError("Fatura cancelada nao pode ser paga.")

        if statement.status == CardStatement.StatementStatus.OPEN:
            raise ValidationError("Fatura deve estar fechada para ser paga.")

        remaining_amount = statement.closed_amount - statement.paid_amount
        payment_amount = amount or remaining_amount

        if payment_amount <= Decimal("0"):
            raise ValidationError("Valor de pagamento deve ser maior que zero.")

        if payment_amount > remaining_amount:
            raise ValidationError("Valor de pagamento nao pode superar o saldo da fatura.")

        payment_account = statement.payment_account or statement.card.payment_account
        if payment_account is None:
            raise ValidationError("Fatura exige conta de pagamento.")

        payment_account.balance -= payment_amount
        payment_account.save(update_fields=["balance", "updated_at"])

        statement.payment_account = payment_account
        statement.paid_amount += payment_amount
        if statement.paid_amount == statement.closed_amount:
            statement.status = CardStatement.StatementStatus.PAID
        else:
            statement.status = CardStatement.StatementStatus.PARTIALLY_PAID

        statement.full_clean()
        statement.save(update_fields=["payment_account", "paid_amount", "status", "updated_at"])

        payment_transaction = Transaction(
            description=f"Pagamento fatura {statement}",
            amount=payment_amount,
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            status=Transaction.PaymentStatus.PAID,
            account=payment_account,
            card=statement.card,
            statement=statement,
            date=date.today(),
        )
        payment_transaction.full_clean()
        payment_transaction.save()

    return statement


def update_statement_status(*, statement, today=None):
    """Atualiza a fatura para atrasada quando passou do vencimento sem pagamento total."""

    today = today or date.today()
    statement = CardStatement.objects.get(pk=statement.pk)

    if statement.status in (
        CardStatement.StatementStatus.CANCELED,
        CardStatement.StatementStatus.PAID,
    ):
        return statement

    if today > statement.due_date and statement.paid_amount < statement.closed_amount:
        statement.status = CardStatement.StatementStatus.LATE
        statement.save(update_fields=["status", "updated_at"])

    return statement
