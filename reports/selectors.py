"""Seletores para as funcionalidades de relatórios."""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from decimal import ROUND_HALF_UP

from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.db.models.functions import ExtractYear

from accounts.models import FinancialAccount
from cards.models import CardStatement
from goals.models import MonthlyGoal
from transactions.models import Transaction


EXCLUDED_STATUSES = [
    Transaction.PaymentStatus.IGNORED,
    Transaction.PaymentStatus.CANCELED,
    Transaction.PaymentStatus.FORECASTED,
]
MONTH_LABELS = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}
CHART_COLORS = [
    "#059669",
    "#0f8bd6",
    "#d9c92f",
    "#e87121",
    "#7c3aed",
    "#64748b",
]


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


def get_category_expense_share(*, year: int, month: int):
    """Monta percentuais de despesas por categoria para exibicao visual."""

    breakdown = get_category_expense_breakdown(year=year, month=month)
    total = sum((item["total_amount"] for item in breakdown), Decimal("0.00"))

    if not total:
        return []

    share_items = []
    for index, item in enumerate(breakdown):
        amount = item["total_amount"]
        percentage = ((amount / total) * Decimal("100")).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
        share_items.append(
            {
                "category_id": item["category_id"],
                "category_name": item["category__name"] or "Sem categoria",
                "total_amount": amount,
                "percentage": int(percentage),
                "color": CHART_COLORS[index % len(CHART_COLORS)],
            }
        )

    return share_items


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


def get_monthly_cashflow_series(*, year: int, month: int, range_months: int = 12):
    """Retorna uma serie mensal de receitas, despesas e saldo para o grafico."""

    range_months = _normalize_range_months(range_months)
    periods = _build_month_periods(year=year, month=month, range_months=range_months)
    period_map = {
        (period["year"], period["month"]): {
            **period,
            "income_total": Decimal("0.00"),
            "expense_total": Decimal("0.00"),
        }
        for period in periods
    }

    first_period = periods[0]
    last_period = periods[-1]
    first_day = date(first_period["year"], first_period["month"], 1)
    last_day = date(
        last_period["year"],
        last_period["month"],
        monthrange(last_period["year"], last_period["month"])[1],
    )

    rows = (
        Transaction.objects.filter(
            date__gte=first_day,
            date__lte=last_day,
            transaction_type__in=[
                Transaction.TransactionType.INCOME,
                Transaction.TransactionType.EXPENSE,
            ],
        )
        .exclude(status__in=EXCLUDED_STATUSES)
        .annotate(period_year=ExtractYear("date"), period_month=ExtractMonth("date"))
        .values("period_year", "period_month", "transaction_type")
        .annotate(total=Sum("amount"))
    )

    for row in rows:
        period_key = (row["period_year"], row["period_month"])
        if period_key not in period_map:
            continue

        total = row["total"] or Decimal("0.00")
        if row["transaction_type"] == Transaction.TransactionType.INCOME:
            period_map[period_key]["income_total"] = total
        if row["transaction_type"] == Transaction.TransactionType.EXPENSE:
            period_map[period_key]["expense_total"] = total

    series = []
    max_visual_amount = Decimal("0.00")

    for period in period_map.values():
        balance = period["income_total"] - period["expense_total"]
        visual_amount = abs(balance)
        max_visual_amount = max(max_visual_amount, visual_amount)
        series.append(
            {
                **period,
                "balance": balance,
                "visual_amount": visual_amount,
                "is_negative": balance < Decimal("0.00"),
                "value_label": _format_compact_amount(balance),
            }
        )

    for item in series:
        item["bar_height"] = _calculate_bar_height(
            amount=item["visual_amount"],
            max_amount=max_visual_amount,
        )

    return series


def get_monthly_dashboard(*, year: int, month: int, range_months: int = 12):
    """Montar o payload completo do painel mensal, incluindo despesas por categoria, patrimônio por moeda, extratos de cartão e resumo de metas."""
    income_total = get_monthly_income_total(year=year, month=month)
    expense_total = get_monthly_expense_total(year=year, month=month)
    
    return{
        "year": year,
        "month": month,
        "range_months": _normalize_range_months(range_months),
        "income_total": income_total,
        "expense_total": expense_total,
        "monthly_balance": income_total - expense_total,
        "cashflow_series": get_monthly_cashflow_series(
            year=year,
            month=month,
            range_months=range_months,
        ),
        "category_expenses": get_category_expense_breakdown(year=year, month=month),
        "category_expense_share": get_category_expense_share(year=year, month=month),
        "net_worth": get_account_net_worth(),
        "card_statements": get_card_statements(year=year, month=month),
        "goal_summary": get_goal_summary(year=year, month=month)
    }


def _normalize_range_months(range_months: int) -> int:
    """Mantem o intervalo do grafico dentro das opcoes da interface."""

    try:
        range_months = int(range_months)
    except (TypeError, ValueError):
        return 12

    if range_months in (6, 12, 24):
        return range_months

    return 12


def _build_month_periods(*, year: int, month: int, range_months: int):
    """Monta meses consecutivos ate o periodo selecionado."""

    current_index = (year * 12) + month - 1
    start_index = current_index - range_months + 1
    periods = []

    for index in range(start_index, current_index + 1):
        period_year = index // 12
        period_month = (index % 12) + 1
        periods.append(
            {
                "year": period_year,
                "month": period_month,
                "label": f"{MONTH_LABELS[period_month]}/{period_year}",
            }
        )

    return periods


def _calculate_bar_height(*, amount, max_amount):
    """Converte valor financeiro em altura percentual com minimo visivel."""

    if max_amount <= Decimal("0.00") or amount <= Decimal("0.00"):
        return 8

    height = int(((amount / max_amount) * Decimal("100")).quantize(Decimal("1")))
    return max(14, height)


def _format_compact_amount(value):
    """Formata valores compactos para rotulos do grafico."""

    sign = "-" if value < Decimal("0.00") else ""
    absolute_value = abs(value)

    if absolute_value >= Decimal("1000.00"):
        compact_value = (absolute_value / Decimal("1000")).quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )
        formatted = f"{compact_value}".replace(".", ",")
        if formatted.endswith(",0"):
            formatted = formatted[:-2]
        return f"{sign}{formatted} mil"

    rounded_value = absolute_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{sign}{rounded_value}"
