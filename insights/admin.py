from django.contrib import admin

from .models import IgnoredPattern, Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    """Configura exibicao e filtros do model Insight no Django Admin."""

    list_display = (
        "title",
        "insight_type",
        "status",
        "suggested_amount",
        "category",
        "created_at",
    )
    list_filter = ("insight_type", "status", "category")
    search_fields = ("title", "message", "source_key")
    ordering = ("-created_at",)


@admin.register(IgnoredPattern)
class IgnoredPatternAdmin(admin.ModelAdmin):
    """Configura exibicao dos padroes silenciados no Django Admin."""

    list_display = ("pattern_key", "reason", "created_at")
    search_fields = ("pattern_key", "reason")
    ordering = ("-created_at",)
