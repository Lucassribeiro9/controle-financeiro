"""Seletores para as funcionalidades de relatórios."""

from django.db.models import Sum
from transactions.models import Transaction
from accounts.models import FinancialAccount
from cards.models import CardStatement
from goals.models import MonthlyGoal
from decimal import Decimal


EXCLUDED_STATUSES = [Transaction.PaymentStatus.IGNORED, Transaction.PaymentStatus.CANCELED, Transaction.PaymentStatus.FORECASTED]

def get_monthly_income_total(*, year: int, month: int):
    """Calcula o total de receitas para um determinado mês e ano."""
    return (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.INCOME, date__year=year, date__month=month
        )
        .exclude(status__in=EXCLUDED_STATUSES)
        .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )

def get_monthly_expense_total(*, year: int, month: int):
    """Calcula o total de despesas para um determinado mês e ano."""
    return (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.EXPENSE, date__year=year, date__month=month
        )
        .exclude(status__in=EXCLUDED_STATUSES)
        .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )

def get_category_expense_breakdown(*, year: int, month: int):
    """Obtém o detalhamento das despesas por categoria para um determinado mês e ano."""
    return list(
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.EXPENSE, date__year=year, date__month=month
        )
        .exclude(status__in=EXCLUDED_STATUSES)
        .values("category_id", "category__name")
        .annotate(total_amount=Sum("amount"))
        .order_by("-total_amount")
    )

def get_account_net_worth():
    """Mostra o patrimônio por moeda."""
    return(
        FinancialAccount.objects.filter(is_active=True)
        .values("currency")
        .annotate(total=Sum("balance"))
        .order_by("currency")
    )

def get_card_statements(*, year: int, month: int):
    """Obtém os extratos de cartão de crédito para um determinado mês e ano."""
    return CardStatement.objects.filter(
        year=year, month=month
    ).select_related("card", "payment_account").order_by("-year", "-month")
    
def get_goal_summary(*, year: int, month: int):
    """Mostrar metas com status e progresso."""
    return(
        MonthlyGoal.objects.filter(year=year, month=month)
        .select_related("goal").order_by("status", "goal__name")
    )
    
def get_monthly_dashboard(*, year: int, month: int):
    """Montar o payload completo do painel mensal, incluindo despesas por categoria, patrimônio por moeda, extratos de cartão e resumo de metas."""
    income_total = get_monthly_income_total(year=year, month=month)
    expense_total = get_monthly_expense_total(year=year, month=month)
    
    return{
        "year": year,
        "month": month,
        "income_total": income_total,
        "expense_total": expense_total,
        "monthly_balance": income_total - expense_total,
        "category_expenses": get_category_expense_breakdown(year=year, month=month),
        "net_worth": get_account_net_worth(),
        "card_statements": get_card_statements(year=year, month=month),
        "goal_summary": get_goal_summary(year=year, month=month)
    }