"""Views do app insights."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.utils import map_service_errors_to_view
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
        return JsonResponse({"error": "Campo limit inválido."}, status=400)

    if limit <= 0:
        return JsonResponse({"error": "Campo limit deve ser positivo."}, status=400)

    results = [_serialize_insight(insight) for insight in get_recent_insights(limit=limit)]
    return JsonResponse({"count": len(results), "results": results})


@require_POST
def approve_insight_view(request: HttpRequest, insight_id: int) -> HttpResponse:
    """Aprova um insight e aplica a acao correspondente."""

    insight = get_object_or_404(Insight, pk=insight_id)

    try:
        approve_insight(insight=insight)
    except ValidationError as exc:
        map_service_errors_to_view(request, exc)
    else:
        messages.success(request, "Insight aprovado com sucesso.")

    return redirect("insights:page")


@require_POST
def ignore_insight_view(request: HttpRequest, insight_id: int) -> HttpResponse:
    """Ignora um insight sem aplicar mudancas."""

    insight = get_object_or_404(Insight, pk=insight_id)
    ignore_insight(insight=insight)
    messages.info(request, "Insight ignorado.")

    return redirect("insights:page")


@require_POST
def silence_insight_view(request: HttpRequest, insight_id: int) -> HttpResponse:
    """Silencia um insight para evitar repeticao futura."""

    insight = get_object_or_404(Insight, pk=insight_id)
    silence_insight(insight=insight)
    messages.info(request, "Insight silenciado.")

    return redirect("insights:page")


@require_GET
def insight_page(request: HttpRequest):
    """Renderiza a pagina de revisao de insights."""

    insights = get_pending_insights()
    return render(
        request,
        "insights/list.html",
        {"insights": insights},
    )
