"""Regras de negocio para parcelamentos."""

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_DOWN

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from cards.services import get_or_create_card_statement
from transactions.models import Transaction

from .models import InstallmentPlan


MONEY = Decimal("0.01")


def create_installment_plan(
    *,
    description,
    total_amount,
    total_installments,
    first_installment_date,
    card,
    category=None,
):
    """Cria um plano de parcelamento e gera suas parcelas."""

    installment_amount = _calculate_base_installment_amount(
        total_amount=total_amount,
        total_installments=total_installments,
    )
    plan = InstallmentPlan(
        description=description,
        total_amount=total_amount,
        installment_amount=installment_amount,
        total_installments=total_installments,
        first_installment_date=first_installment_date,
        card=card,
        category=category,
    )
    plan.full_clean()

    with db_transaction.atomic():
        plan.save()
        generate_installment_transactions(plan=plan)

    return plan


def generate_installment_transactions(*, plan):
    """Gera transacoes de compra no cartao para cada parcela."""

    plan = InstallmentPlan.objects.select_related("card", "category").get(pk=plan.pk)
    if plan.transactions.exists():
        raise ValidationError("Parcelas ja foram geradas para este parcelamento.")

    transactions = []
    installment_amounts = _calculate_installment_amounts(
        total_amount=plan.total_amount,
        total_installments=plan.total_installments,
    )

    for index, amount in enumerate(installment_amounts, start=1):
        installment_date = _add_months(
            source_date=plan.first_installment_date,
            months=index - 1,
        )
        statement = get_or_create_card_statement(
            card=plan.card,
            transaction_date=installment_date,
        )
        transaction = Transaction(
            description=f"{plan.description} ({index}/{plan.total_installments})",
            amount=amount,
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=plan.card,
            category=plan.category,
            date=installment_date,
            statement=statement,
            installment_plan=plan,
            installment_number=index,
        )
        transaction.full_clean()
        transaction.save()
        transactions.append(transaction)

    return transactions


def cancel_installment_plan(*, plan):
    """Cancela o plano sem apagar parcelas ja geradas."""

    with db_transaction.atomic():
        plan = InstallmentPlan.objects.select_for_update().get(pk=plan.pk)

        if plan.status == InstallmentPlan.Status.COMPLETED:
            raise ValidationError("Parcelamento concluido nao pode ser cancelado.")

        plan.status = InstallmentPlan.Status.CANCELED
        plan.save(update_fields=["status", "updated_at"])

    return plan


def get_installment_progress(*, plan):
    """Retorna progresso de parcelas geradas/pagas para um plano."""

    transactions = plan.transactions.all()
    generated_count = transactions.count()
    paid_count = transactions.filter(status=Transaction.PaymentStatus.PAID).count()

    return {
        "generated_count": generated_count,
        "paid_count": paid_count,
        "remaining_count": max(plan.total_installments - paid_count, 0),
        "generated_amount": sum(
            (transaction.amount for transaction in transactions),
            Decimal("0.00"),
        ),
    }


def _calculate_base_installment_amount(*, total_amount, total_installments):
    """Calcula a parcela base arredondando centavos para baixo."""

    return (total_amount / Decimal(total_installments)).quantize(
        MONEY,
        rounding=ROUND_DOWN,
    )


def _calculate_installment_amounts(*, total_amount, total_installments):
    """Calcula parcelas garantindo que a soma feche com o total."""

    base_amount = _calculate_base_installment_amount(
        total_amount=total_amount,
        total_installments=total_installments,
    )
    amounts = [base_amount for _ in range(total_installments)]
    amounts[-1] = total_amount - sum(amounts[:-1], Decimal("0.00"))
    return amounts


def _add_months(*, source_date, months):
    """Soma meses preservando dia quando possivel."""

    month_index = source_date.month - 1 + months
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(source_date.day, monthrange(year, month)[1])
    return date(year, month, day)
