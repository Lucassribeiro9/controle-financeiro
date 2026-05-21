from django.contrib import admin

from .models import AccountYieldConfig, ReferenceRate


@admin.register(ReferenceRate)
class ReferenceRateAdmin(admin.ModelAdmin):
    """Configura exibicao de taxas de referencia no Django Admin."""

    list_display = ("rate_type", "date", "value", "periodicity", "source")
    list_filter = ("rate_type", "periodicity", "date")
    search_fields = ("source", "notes")
    ordering = ("-date", "rate_type")


@admin.register(AccountYieldConfig)
class AccountYieldConfigAdmin(admin.ModelAdmin):
    """Configura exibicao de rendimentos por conta no Django Admin."""

    list_display = ("account", "yield_type", "cdi_percentage", "is_active")
    list_filter = ("yield_type", "is_active")
    search_fields = ("account__name", "account__institution__name")
    ordering = ("account__name",)
