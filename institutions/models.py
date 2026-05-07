from django.db import models

# Create your models here.

class Institution(models.Model):
    """Model que representa a instituição. Pode ser um banco, uma corretora, etc."""
    name = models.CharField("Nome", max_length=200, unique=True)
    official_name = models.CharField("Razão Social", max_length=255, blank=True)
    code = models.CharField("Código", max_length=10, unique=True, blank=True)
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    
    class Meta:
        """Meta class para definir o nome da tabela, os nomes legíveis e a ordenação padrão."""
        verbose_name = "Instituição"
        verbose_name_plural = "Instituições"
        ordering = ['name']
        
    def __str__(self) -> str:
        return self.name