from django.contrib import admin
from .models import Institution

# Register your models here.
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    """Admin class para o modelo Institution, definindo os campos a serem exibidos e as opções de busca."""
    # Campos a serem exibidos na lista de instituições
    list_display = ('name', 'official_name', 'code', 'is_active', 'created_at', 'updated_at')
    
    # Campos para busca
    search_fields = ('name', 'official_name', 'code')
    # Filtro para os ativos
    list_filter = ('is_active',)
    # Ordenação padrão por nome
    ordering = ('name',)