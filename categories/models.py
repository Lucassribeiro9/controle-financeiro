from django.db import models


class Category(models.Model):
    """Representa uma categoria financeira com suporte a hierarquia simples."""

    name = models.CharField("Nome", max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="Categoria pai",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        """Configura metadados para ordenacao e nomes legiveis."""

        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["name"]

    def __str__(self) -> str:
        """Retorna o nome amigavel da categoria."""

        return self.name
