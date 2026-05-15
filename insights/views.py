"""Views do app insights."""

from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .models import Insight
from .selectors import get_insights_by_status, get_pending_insights, get_recent_insights
from .services import approve_insight, ignore_insight, silence_insight


def _serialize_insight(insight: Insight) -> dict:
    """Serializa um insight para respostas JSON."""

    return {
        "id": insight.id,
        "title": insight.title,
        "message": insight.message,
        "insight_type": insight.insight_type,
        "status": insight.status,
        "suggested_amount": (
            str(insight.suggested_amount)
            if insight.suggested_amount is not None
            else None
        ),
        "category_id": insight.category_id,
        "recurrence_id": insight.recurrence_id,
        "monthly_goal_id": insight.monthly_goal_id,
        "source_key": insight.source_key,
        "created_at": insight.created_at.isoformat(),
    }


@require_GET
def insight_list(request: HttpRequest) -> JsonResponse:
    """Lista insights para revisao do usuario."""

    status = request.GET.get("status")
    if status:
        insights = get_insights_by_status(status=status)
    else:
        insights = get_pending_insights()

    results = [_serialize_insight(insight) for insight in insights]
    return JsonResponse({"count": len(results), "results": results})


@require_GET
def recent_insights(request: HttpRequest) -> JsonResponse:
    """Lista insights recentes para historico curto."""

    limit_raw = request.GET.get("limit", "10")
    try:
        limit = int(limit_raw)
    except ValueError:
        return JsonResponse({"error": "Campo limit invalido."}, status=400)

    if limit <= 0:
        return JsonResponse({"error": "Campo limit deve ser positivo."}, status=400)

    results = [_serialize_insight(insight) for insight in get_recent_insights(limit=limit)]
    return JsonResponse({"count": len(results), "results": results})


@require_POST
def approve_insight_view(request: HttpRequest, insight_id: int) -> JsonResponse:
    """Aprova um insight e aplica a acao correspondente."""

    insight = get_object_or_404(Insight, pk=insight_id)

    try:
        approved = approve_insight(insight=insight)
    except ValidationError as exc:
        return JsonResponse({"error": exc.message_dict}, status=400)

    return JsonResponse(_serialize_insight(approved))


@require_POST
def ignore_insight_view(request: HttpRequest, insight_id: int) -> JsonResponse:
    """Ignora um insight sem aplicar mudancas."""

    insight = get_object_or_404(Insight, pk=insight_id)
    ignored = ignore_insight(insight=insight)

    return JsonResponse(_serialize_insight(ignored))


@require_POST
def silence_insight_view(request: HttpRequest, insight_id: int) -> JsonResponse:
    """Silencia um insight para evitar repeticao futura."""

    insight = get_object_or_404(Insight, pk=insight_id)
    silenced = silence_insight(insight=insight)

    return JsonResponse(_serialize_insight(silenced))
