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

    @property
    def limit_progress_percent(self):
        """Calcula a porcentagem de uso do limite de gastos."""
        limit = getattr(self, "limit_amount", None)
        if limit is None or limit <= 0:
            return None
        spent = getattr(self, "monthly_spent", 0) or 0
        return (spent / limit) * 100

    @property
    def limit_status(self):
        """Classifica a tendencia/status de uso do limite."""
        percent = self.limit_progress_percent
        if percent is None:
            return None
        if percent < 80:
            return "ok"
        elif percent < 100:
            return "at_risk"
        else:
            return "exceeded"

