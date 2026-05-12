from django.contrib import admin
from .models import Recurrence

# Register your models here.


@admin.register(Recurrence)
class RecurrenceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "recurrence_type",
        "frequency",
        "expected_day",
        "expected_amount",
        "is_active",
    )
    list_filter = ("recurrence_type", "frequency", "is_active")
    search_fields = ("name",)
    ordering = ("expected_day", "name")
