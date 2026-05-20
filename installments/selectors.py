"""Seletores para parcelamentos."""

from django.db.models import Count

from .models import InstallmentPlan


def get_active_installment_plans():
    """Lista parcelamentos ativos com relacionamentos principais."""

    return (
        InstallmentPlan.objects.filter(status=InstallmentPlan.Status.ACTIVE)
        .select_related("card", "category")
        .annotate(generated_count=Count("transactions"))
        .order_by("first_installment_date", "description")
    )


def get_installment_plan_detail(*, plan_id):
    """Busca detalhe de um parcelamento."""

    return (
        InstallmentPlan.objects.select_related("card", "category")
        .prefetch_related("transactions", "transactions__statement")
        .get(pk=plan_id)
    )


def get_installments_by_card(*, card):
    """Lista parcelamentos de um cartao."""

    return (
        InstallmentPlan.objects.filter(card=card)
        .select_related("card", "category")
        .annotate(generated_count=Count("transactions"))
        .order_by("status", "first_installment_date", "description")
    )


def get_installments_ending_soon(*, limit=5):
    """Lista parcelamentos ativos mais proximos de terminar."""

    return (
        InstallmentPlan.objects.filter(status=InstallmentPlan.Status.ACTIVE)
        .select_related("card", "category")
        .annotate(generated_count=Count("transactions"))
        .order_by("total_installments", "first_installment_date")[:limit]
    )
