from django.contrib import admin

from transactions.models import Transaction, Transfer


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Configura exibicao e filtros do model Transaction no Django Admin."""

    list_display = (
        "description",
        "amount",
        "transaction_type",
        "status",
        "account",
        "card",
        "category",
        "date",
    )
    search_fields = ("description", "account__name", "card__name", "category__name")
    list_filter = ("transaction_type", "status", "date", "account", "card", "category")
    ordering = ("-date", "-created_at")


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    """Configura exibicao e filtros do model Transfer no Django Admin."""

    list_display = (
        "description",
        "amount",
        "from_account",
        "destination_account",
        "date",
    )
    search_fields = ("description", "from_account__name", "destination_account__name")
    list_filter = ("date", "from_account", "destination_account")
    ordering = ("-date", "-created_at")
