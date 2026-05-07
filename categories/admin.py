from django.contrib import admin

from categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Configura exibicao e busca de categorias no Django Admin."""

    list_display = ("name", "parent", "is_active", "created_at", "updated_at")
    search_fields = ("name", "parent__name")
    list_filter = ("is_active",)
    ordering = ("name",)
