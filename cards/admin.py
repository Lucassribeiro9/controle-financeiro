from django.contrib import admin

from cards.models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Configura exibicao e filtros do model Card no Django Admin."""

    list_display = (
        "name",
        "institution",
        "card_type",
        "credit_limit",
        "estimated_balance",
        "statement_closing_day",
        "statement_due_day",
        "is_active",
    )
    search_fields = ("name", "institution__name")
    list_filter = ("card_type", "institution", "is_active")
    ordering = ("name",)
