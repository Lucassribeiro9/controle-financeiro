from django.contrib import admin
from .models import ImportedTransaction

# Register your models here.
@admin.register(ImportedTransaction)
class ImportedTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "normalized_description",
        "amount",
        "status",
        "source_type",
    )
    list_filter = ("status", "source_type", "date")
    search_fields = ("normalized_description", "raw_description")