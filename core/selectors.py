"""Selectors para montar dados da home operacional."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from cards.models import CardStatement
from categories.selectors import get_categories_at_risk
from goals.models import MonthlyGoal
from imports.models import ImportedTransaction
from insights.models import Insight
from recurrences.models import Recurrence
from transactions.constants import SPENDING_TRANSACTION_TYPES
from transactions.models import Transaction, Transfer


REALIZED_STATUSES = [Transaction.PaymentStatus.PAID]
PENDING_STATUSES = [
    Transaction.PaymentStatus.PENDING,
    Transaction.PaymentStatus.PARTIALLY_PAID,
    Transaction.PaymentStatus.LATE,
]
FORECAST_STATUSES = [Transaction.PaymentStatus.FORECASTED]
INCOME_TYPES = [Transaction.TransactionType.INCOME]
SUMMARY_CARD_STATUSES = {
    "realized": REALIZED_STATUSES,
    "pending": PENDING_STATUSES,
    "forecasted": FORECAST_STATUSES,
}
SUMMARY_CARD_LABELS = {
    "realized": "Realizado",
    "pending": "Pendente",
    "forecasted": "Previsto",
}


def get_operational_home_context(*, today=None) -> dict:
    """Retorna o contrato de dados minimo para a Home Operacional."""

    reference_date = today or timezone.localdate()
    year = reference_date.year
    month = reference_date.month

    summary = _build_month_summary(year=year, month=month)
    alerts = _build_alerts(today=reference_date, year=year, month=month)
    pending_items = _build_pending_items(year=year, month=month)
    quick_actions = _build_quick_actions()
    categories_at_risk = list(get_categories_at_risk(reference_date))
    empty_states = _build_empty_states(
        summary=summary,
        alerts=alerts,
        pending_items=pending_items,
        categories_at_risk=categories_at_risk,
    )

    return {
        "summary": summary,
        "alerts": alerts,
        "pending_items": pending_items,
        "quick_actions": quick_actions,
        "categories_at_risk": categories_at_risk,
        "empty_states": empty_states,
    }


def get_summary_card_detail(*, card: str, today=None) -> dict:
    """Lista os lancamentos que compoem um card do resumo financeiro.

    Usa os mesmos filtros das somas da home, entao os subtotais retornados
    sempre coincidem com os valores exibidos no card.
    """

    if card not in SUMMARY_CARD_LABELS:
        raise ValueError(f"Card de resumo desconhecido: {card}")

    reference_date = today or timezone.localdate()
    year = reference_date.year
    month = reference_date.month

    income = _list_card_transactions(
        card=card, year=year, month=month, transaction_types=INCOME_TYPES
    )
    expenses = _list_card_transactions(
        card=card, year=year, month=month, transaction_types=SPENDING_TRANSACTION_TYPES
    )
    if card == "forecasted":
        income_forecasts, expense_forecasts = _classify_recurring_forecasts(
            year=year, month=month
        )
        income = _sort_transactions([*income, *income_forecasts])
        expenses = _sort_transactions([*expenses, *expense_forecasts])

    income_total = sum((item.amount for item in income), Decimal("0.00"))
    expenses_total = sum((item.amount for item in expenses), Decimal("0.00"))

    return {
        "card": card,
        "label": SUMMARY_CARD_LABELS[card],
        "period": {"year": year, "month": month},
        "income": {"transactions": income, "total": income_total},
        "expenses": {"transactions": expenses, "total": expenses_total},
        "net": income_total - expenses_total,
    }


def _list_card_transactions(
    *, card: str, year: int, month: int, transaction_types: list[str]
) -> list[Transaction]:
    """Lista transacoes de um card para os tipos informados."""

    queryset = _filter_transactions(
        year=year,
        month=month,
        transaction_types=transaction_types,
        statuses=SUMMARY_CARD_STATUSES[card],
    ).select_related("account", "category", "card", "statement")
    return _sort_transactions(list(queryset))


def _sort_transactions(transactions: list[Transaction]) -> list[Transaction]:
    """Ordena por data e criacao, do mais recente ao mais antigo."""

    return sorted(
        transactions,
        key=lambda transaction: (transaction.date, transaction.created_at),
        reverse=True,
    )


def _build_month_summary(*, year: int, month: int) -> dict:
    """Monta o resumo financeiro do mes por status operacional."""

    return {
        "period": {"year": year, "month": month},
        "realized": _build_transaction_totals(
            year=year,
            month=month,
            statuses=REALIZED_STATUSES,
        ),
        "pending": _build_transaction_totals(
            year=year,
            month=month,
            statuses=PENDING_STATUSES,
        ),
        "forecasted": _build_forecasted_totals(year=year, month=month),
        "transfers": _sum_transfers(year=year, month=month),
    }


def _build_transaction_totals(*, year: int, month: int, statuses: list[str]) -> dict:
    """Soma receitas e despesas de um periodo para os status informados."""

    income = _sum_transactions(
        year=year,
        month=month,
        transaction_types=INCOME_TYPES,
        statuses=statuses,
    )
    expenses = _sum_transactions(
        year=year,
        month=month,
        transaction_types=SPENDING_TRANSACTION_TYPES,
        statuses=statuses,
    )

    return {
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
    }


def _filter_transactions(
    *,
    year: int,
    month: int,
    transaction_types: list[str],
    statuses: list[str],
):
    """Filtra transacoes por periodo, tipos e status.

    Esta e a unica query que define o que entra em cada card do resumo; as
    somas da home e a listagem do detalhe partem dela.
    """

    return Transaction.objects.filter(
        date__year=year,
        date__month=month,
        transaction_type__in=transaction_types,
        status__in=statuses,
    )


def _sum_transactions(
    *,
    year: int,
    month: int,
    transaction_types: list[str],
    statuses: list[str],
) -> Decimal:
    """Soma transacoes filtradas por periodo, tipos e status."""

    return _filter_transactions(
        year=year,
        month=month,
        transaction_types=transaction_types,
        statuses=statuses,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


def _sum_transfers(*, year: int, month: int) -> Decimal:
    """Soma transferencias internas do periodo sem trata-las como receita."""

    return (
        Transfer.objects.filter(date__year=year, date__month=month).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


def _build_forecasted_totals(*, year: int, month: int) -> dict:
    """Monta totais previstos incluindo previsoes comuns e recorrentes."""

    totals = _build_transaction_totals(
        year=year,
        month=month,
        statuses=FORECAST_STATUSES,
    )
    recurring_totals = _sum_recurring_forecasts(year=year, month=month)

    income = totals["income"] + recurring_totals["income"]
    expenses = totals["expenses"] + recurring_totals["expenses"]
    return {
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
    }


def _sum_recurring_forecasts(*, year: int, month: int) -> dict:
    """Soma previsoes recorrentes geradas e classificadas pela recorrencia."""

    income_forecasts, expense_forecasts = _classify_recurring_forecasts(
        year=year,
        month=month,
    )

    return {
        "income": sum((forecast.amount for forecast in income_forecasts), Decimal("0.00")),
        "expenses": sum(
            (forecast.amount for forecast in expense_forecasts), Decimal("0.00")
        ),
    }


def _classify_recurring_forecasts(
    *, year: int, month: int
) -> tuple[list[Transaction], list[Transaction]]:
    """Separa previsoes recorrentes em receitas e despesas pela recorrencia."""

    income_forecasts = []
    expense_forecasts = []
    for forecast in _get_generated_recurring_forecasts(year=year, month=month):
        if forecast.recurrence.recurrence_type == Recurrence.RecurrenceType.INCOME:
            income_forecasts.append(forecast)
        else:
            expense_forecasts.append(forecast)

    return income_forecasts, expense_forecasts


def _get_generated_recurring_forecasts(*, year: int, month: int) -> list[Transaction]:
    """Lista previsoes vinculadas a uma recorrencia existente."""

    return list(
        Transaction.objects.filter(
            date__year=year,
            date__month=month,
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            recurrence__isnull=False,
        ).select_related("recurrence")
    )


def _build_alerts(*, today, year: int, month: int) -> list[dict]:
    """Monta alertas prioritarios da home em ordem de importancia."""

    return [
        *_get_due_statement_alerts(today=today),
        *_get_pending_import_alerts(),
        *_get_goal_risk_alerts(year=year, month=month),
    ]


def _get_due_statement_alerts(*, today) -> list[dict]:
    """Lista faturas vencidas ou proximas do vencimento como alertas."""

    due_until = today + timedelta(days=15)
    statements = (
        CardStatement.objects.filter(due_date__lte=due_until)
        .exclude(
            status__in=[
                CardStatement.StatementStatus.PAID,
                CardStatement.StatementStatus.CANCELED,
            ]
        )
        .select_related("card")
        .order_by("due_date", "card__name")[:5]
    )

    return [
        {
            "type": "card_statement",
            "priority": "high",
            "title": f"Fatura {statement.card.name}",
            "description": f"Vence em {statement.due_date:%d/%m/%Y}",
            "amount": statement.closed_amount or statement.expected_amount,
            "url": reverse("cards:statement-detail", args=[statement.id]),
            "due_date": statement.due_date,
        }
        for statement in statements
    ]


def _count_imports_awaiting_review() -> int:
    """Conta importacoes pendentes e duplicadas, como a aba Pendentes da revisao."""

    return ImportedTransaction.objects.filter(
        status__in=(
            ImportedTransaction.Status.PENDING,
            ImportedTransaction.Status.DUPLICATE,
        )
    ).count()


def _get_pending_import_alerts() -> list[dict]:
    """Retorna alerta agregado para importacoes pendentes de revisao."""

    pending_count = _count_imports_awaiting_review()

    if pending_count == 0:
        return []

    return [
        {
            "type": "imports",
            "priority": "medium",
            "title": "Importacoes pendentes",
            "description": f"{pending_count} lancamento(s) aguardando revisao",
            "count": pending_count,
            "url": reverse("imports:review-page"),
        }
    ]


def _get_goal_risk_alerts(*, year: int, month: int) -> list[dict]:
    """Lista metas mensais em risco no periodo informado."""

    monthly_goals = (
        MonthlyGoal.objects.filter(year=year, month=month)
        .select_related("goal", "goal__category")
        .order_by("goal__name")
    )

    alerts = []
    for monthly_goal in monthly_goals:
        if not _is_goal_at_risk(monthly_goal):
            continue

        alerts.append(
            {
                "type": "goal",
                "priority": "medium",
                "title": monthly_goal.goal.name,
                "description": "Meta mensal em risco",
                "current_amount": monthly_goal.current_amount,
                "target_amount": monthly_goal.target_amount,
                "url": reverse("goals:monthly-goals"),
            }
        )

    return alerts[:5]


def _is_goal_at_risk(monthly_goal: MonthlyGoal) -> bool:
    """Indica se uma meta mensal deve aparecer como risco operacional."""

    if monthly_goal.status in [
        MonthlyGoal.Status.AT_RISK,
        MonthlyGoal.Status.MISSED,
    ]:
        return True

    if monthly_goal.target_amount <= Decimal("0.00"):
        return False

    return monthly_goal.current_amount >= monthly_goal.target_amount * Decimal("0.80")


def _build_pending_items(*, year: int, month: int) -> list[dict]:
    """Monta pendencias acionaveis que apontam para seus fluxos completos."""

    items = []

    pending_imports = _count_imports_awaiting_review()
    if pending_imports:
        items.append(
            {
                "type": "imports",
                "title": "Revisar importacoes",
                "count": pending_imports,
                "url": reverse("imports:review-page"),
            }
        )

    pending_insights = Insight.objects.filter(status=Insight.Status.PENDING).count()
    if pending_insights:
        items.append(
            {
                "type": "insights",
                "title": "Revisar insights",
                "count": pending_insights,
                "url": reverse("insights:page"),
            }
        )

    forecasted_transactions = len(
        _get_generated_recurring_forecasts(year=year, month=month)
    )
    if forecasted_transactions:
        items.append(
            {
                "type": "recurrences",
                "title": "Revisar recorrencias previstas",
                "count": forecasted_transactions,
                "url": reverse("recurrences:forecasts-page", args=[year, month]),
            }
        )

    return items


def _build_quick_actions() -> list[dict]:
    """Retorna atalhos fixos para os fluxos principais do app."""

    return [
        {
            "title": "Novo lancamento",
            "url": reverse("transactions:create"),
        },
        {
            "title": "Nova transferencia",
            "url": reverse("transactions:transfer-create"),
        },
        {
            "title": "Revisar importacoes",
            "url": reverse("imports:review-page"),
        },
        {
            "title": "Ver faturas",
            "url": reverse("cards:statements"),
        },
    ]


def _build_empty_states(
    *,
    summary: dict,
    alerts: list[dict],
    pending_items: list[dict],
    categories_at_risk: list,
) -> dict:
    """Monta estados vazios com CTAs para os blocos da home."""

    return {
        "summary": {
            "is_empty": _is_summary_empty(summary),
            "title": "Nenhum lancamento neste mes",
            "cta_label": "Criar lancamento",
            "cta_url": reverse("transactions:create"),
        },
        "alerts": {
            "is_empty": len(alerts) == 0,
            "title": "Nenhum alerta prioritario",
            "cta_label": "Ver dashboard mensal",
            "cta_url": "/reports/month/",
        },
        "pending_items": {
            "is_empty": len(pending_items) == 0,
            "title": "Nenhuma pendencia operacional",
            "cta_label": "Ver recorrencias",
            "cta_url": reverse("recurrences:forecasts-filter-page"),
        },
        "categories_at_risk": {
            "is_empty": len(categories_at_risk) == 0,
            "title": "Excelente! Todos os limites sob controle.",
            "cta_label": "Ver categorias",
            "cta_url": reverse("categories:list"),
        },
    }



def _is_summary_empty(summary: dict) -> bool:
    """Indica se o resumo mensal nao possui valores financeiros."""

    total = Decimal("0.00")
    for group_name in ["realized", "pending", "forecasted"]:
        group = summary[group_name]
        total += group["income"] + group["expenses"]

    return total == Decimal("0.00")
