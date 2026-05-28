"""Selectors para montar dados da home operacional."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from cards.models import CardStatement
from goals.models import MonthlyGoal
from imports.models import ImportedTransaction
from insights.models import Insight
from recurrences.models import Recurrence
from transactions.models import Transaction, Transfer


REALIZED_STATUSES = [Transaction.PaymentStatus.PAID]
PENDING_STATUSES = [
    Transaction.PaymentStatus.PENDING,
    Transaction.PaymentStatus.PARTIALLY_PAID,
    Transaction.PaymentStatus.LATE,
]
FORECAST_STATUSES = [Transaction.PaymentStatus.FORECASTED]


def get_operational_home_context(*, today=None) -> dict:
    """Retorna o contrato de dados minimo para a Home Operacional."""

    reference_date = today or timezone.localdate()
    year = reference_date.year
    month = reference_date.month

    summary = _build_month_summary(year=year, month=month)
    alerts = _build_alerts(today=reference_date, year=year, month=month)
    pending_items = _build_pending_items(year=year, month=month)
    quick_actions = _build_quick_actions()
    empty_states = _build_empty_states(
        summary=summary,
        alerts=alerts,
        pending_items=pending_items,
    )

    return {
        "summary": summary,
        "alerts": alerts,
        "pending_items": pending_items,
        "quick_actions": quick_actions,
        "empty_states": empty_states,
    }


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
        transaction_type=Transaction.TransactionType.INCOME,
        statuses=statuses,
    )
    expenses = _sum_transactions(
        year=year,
        month=month,
        transaction_type=Transaction.TransactionType.EXPENSE,
        statuses=statuses,
    )

    return {
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
    }


def _sum_transactions(
    *,
    year: int,
    month: int,
    transaction_type: str,
    statuses: list[str],
) -> Decimal:
    """Soma transacoes filtradas por periodo, tipo e status."""

    return (
        Transaction.objects.filter(
            date__year=year,
            date__month=month,
            transaction_type=transaction_type,
            status__in=statuses,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )


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

    forecasts = _get_generated_recurring_forecasts(year=year, month=month)
    recurrence_names = [
        recurrence_name
        for forecast in forecasts
        if (recurrence_name := _extract_generated_recurrence_name(forecast.description))
    ]
    recurrences_by_name = {
        recurrence.name: recurrence
        for recurrence in Recurrence.objects.filter(name__in=recurrence_names)
    }

    income = Decimal("0.00")
    expenses = Decimal("0.00")
    for forecast in forecasts:
        recurrence = recurrences_by_name.get(
            _extract_generated_recurrence_name(forecast.description)
        )
        if recurrence is None:
            continue

        if recurrence.recurrence_type == Recurrence.RecurrenceType.INCOME:
            income += forecast.amount
        else:
            expenses += forecast.amount

    return {
        "income": income,
        "expenses": expenses,
    }


def _get_generated_recurring_forecasts(*, year: int, month: int) -> list[Transaction]:
    """Lista previsoes recorrentes geradas pelo fluxo de recorrencias."""

    forecasts = list(
        Transaction.objects.filter(
            date__year=year,
            date__month=month,
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
        )
    )
    recurrence_names = [
        recurrence_name
        for forecast in forecasts
        if (recurrence_name := _extract_generated_recurrence_name(forecast.description))
    ]
    existing_names = set(
        Recurrence.objects.filter(name__in=recurrence_names).values_list(
            "name",
            flat=True,
        )
    )
    return [
        forecast
        for forecast in forecasts
        if _extract_generated_recurrence_name(forecast.description) in existing_names
    ]


def _extract_generated_recurrence_name(description: str) -> str | None:
    """Extrai o nome da recorrencia do padrao gerado pelo service."""

    prefix = "[REC] "
    if description.startswith(prefix):
        return description[len(prefix) :]
    return None


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


def _get_pending_import_alerts() -> list[dict]:
    """Retorna alerta agregado para importacoes pendentes de revisao."""

    pending_count = ImportedTransaction.objects.filter(
        status=ImportedTransaction.Status.PENDING
    ).count()

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

    pending_imports = ImportedTransaction.objects.filter(
        status=ImportedTransaction.Status.PENDING
    ).count()
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
    }


def _is_summary_empty(summary: dict) -> bool:
    """Indica se o resumo mensal nao possui valores financeiros."""

    total = Decimal("0.00")
    for group_name in ["realized", "pending", "forecasted"]:
        group = summary[group_name]
        total += group["income"] + group["expenses"]

    return total == Decimal("0.00")
