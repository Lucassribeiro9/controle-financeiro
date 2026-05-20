from django.contrib import admin

from installments.models import InstallmentPlan


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "card",
        "total_amount",
        "total_installments",
        "status",
        "first_installment_date",
    )
    list_filter = ("status", "card", "category")
    search_fields = ("description", "card__name", "category__name")
