from django.db import models


class Category(models.Model):
    """Representa uma categoria financeira com suporte a hierarquia simples."""

    class IconChoices(models.TextChoices):
        HOME = 'home', 'Casa'
        CARD = 'card', 'Cartão'
        DOLLAR = 'dollar', 'Dinheiro'
        TAG = 'tag', 'Etiqueta'
        CHART = 'chart', 'Gráfico'

    class ColorChoices(models.TextChoices):
        SLATE = 'slate', 'Cinza'
        RED = 'red', 'Vermelho'
        GREEN = 'green', 'Verde'
        BLUE = 'blue', 'Azul'
        YELLOW = 'yellow', 'Amarelo'

    name = models.CharField("Nome", max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="Categoria pai",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    icon = models.CharField(
        "Ícone",
        max_length=50,
        choices=IconChoices.choices,
        null=True,
        blank=True,
    )
    color = models.CharField(
        "Cor",
        max_length=50,
        choices=ColorChoices.choices,
        null=True,
        blank=True,
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
