"""Seletores para as funcionalidades de insights."""

from .models import IgnoredPattern, Insight


def get_pending_insights():
    """Lista insights pendentes para decisao do usuario."""

    return (
        Insight.objects.filter(status=Insight.Status.PENDING)
        .select_related("category", "recurrence", "monthly_goal", "monthly_goal__goal")
        .order_by("-created_at")
    )


def get_insights_by_status(*, status):
    """Lista insights filtrados por status."""

    return (
        Insight.objects.filter(status=status)
        .select_related("category", "recurrence", "monthly_goal", "monthly_goal__goal")
        .order_by("-created_at")
    )


def get_recent_insights(*, limit=10):
    """Lista insights recentes para historico curto ou dashboard."""

    return (
        Insight.objects.select_related(
            "category",
            "recurrence",
            "monthly_goal",
            "monthly_goal__goal",
        )
        .order_by("-created_at")[:limit]
    )


def get_ignored_patterns():
    """Lista padroes silenciados pelo usuario."""

    return IgnoredPattern.objects.order_by("-created_at")
