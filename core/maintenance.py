"""Rotina diaria de manutencao (ADR-013).

Concentra o que antes acontecia em GETs: previsoes de recorrencias, fechamento e
atraso de faturas, recalculo de metas e insights do mes anterior. Cada passo roda
na propria transacao e uma falha nao impede os demais.
"""

from dataclasses import dataclass, field
from datetime import date

from django.db import transaction
from django.utils import timezone

from cards.services import auto_close_due_statements, mark_late_statements
from goals.services import refresh_monthly_goals
from insights.services import generate_monthly_insights
from recurrences.services import generate_monthly_recurrences_forecasts


@dataclass
class StepResult:
    """Resultado de um passo da rotina."""

    name: str
    count: int = 0
    error: str = ""


@dataclass
class MaintenanceReport:
    """Resultado agregado da rotina."""

    steps: list[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(not step.error for step in self.steps)


def _previous_month(*, year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def run_daily_maintenance(*, today: date | None = None) -> MaintenanceReport:
    """Executa os passos em ordem fixa, isolando falhas por passo."""

    today = today or timezone.localdate()
    year, month = today.year, today.month
    prev_year, prev_month = _previous_month(year=year, month=month)

    steps = [
        (
            "previsoes",
            lambda: generate_monthly_recurrences_forecasts(year=year, month=month),
        ),
        ("faturas_fechadas", lambda: auto_close_due_statements(today=today)),
        ("faturas_atrasadas", lambda: mark_late_statements(today=today)),
        ("metas", lambda: refresh_monthly_goals(year=year, month=month)),
        (
            "insights",
            lambda: len(generate_monthly_insights(year=prev_year, month=prev_month)),
        ),
    ]

    report = MaintenanceReport()
    for name, action in steps:
        result = StepResult(name=name)
        try:
            with transaction.atomic():
                result.count = action()
        except Exception as exc:  # noqa: BLE001 - passo isolado, erro vai ao relatorio
            result.error = str(exc) or exc.__class__.__name__
        report.steps.append(result)

    return report
