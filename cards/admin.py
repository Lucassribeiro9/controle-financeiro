from django.contrib import admin

from cards.models import Card, CardStatement


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

# Criando admin do CardStatement
@admin.register(CardStatement)
class CardStatementAdmin(admin.ModelAdmin):
    """Configura exibicao e filtros do model CardStatement no Django Admin."""

    list_display = (
        "card",
        "month",
        "year",
        "status",
        "expected_amount",
        "paid_amount",
        "closed_amount",
        "due_date",
        "payment_account"
    )
    search_fields = ("card__name", "card__institution__name")
    list_filter = ("month", "year", "status", "card", "due_date")
    ordering = ("-year", "-month", "-card__name")