from django.contrib import admin

from accounts.models import FinancialAccount


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    """Configura listagem e busca de contas financeiras no Django Admin."""

    list_display = (
        "name",
        "institution",
        "account_type",
        "currency",
        "balance",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "institution__name")
    list_filter = ("account_type", "currency", "is_active", "institution")
    ordering = ("name",)
