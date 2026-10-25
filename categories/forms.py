"""Forms do app categories."""

from django import forms
from django.utils import timezone

from core.forms import BRDecimalField, BRIntegerField
from core.templatetags.money import month_name

from .models import Category


class CategoryForm(forms.ModelForm):
    """Formulario para cadastrar e editar categorias."""

    class Meta:
        model = Category
        fields = ["name", "parent", "icon", "color", "is_active"]
        labels = {
            "name": "Nome",
            "parent": "Categoria pai",
            "icon": "Ícone",
            "color": "Cor",
            "is_active": "Ativa",
        }

    def __init__(self, *args, **kwargs):
        """Configura categorias disponiveis como pai."""

        super().__init__(*args, **kwargs)
        parent_queryset = Category.objects.order_by("name")
        if self.instance.pk:
            parent_queryset = parent_queryset.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parent_queryset

    def clean_name(self):
        """Normaliza espacos do nome."""

        return self.cleaned_data["name"].strip()

    def clean(self):
        """Valida duplicidade de nome e autorreferencia."""

        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        parent = cleaned_data.get("parent")

        if name:
            duplicate_categories = Category.objects.filter(name__iexact=name)
            if self.instance.pk:
                duplicate_categories = duplicate_categories.exclude(pk=self.instance.pk)

            if duplicate_categories.exists():
                self.add_error("name", "Já existe uma categoria com este nome.")

        if self.instance.pk and parent and parent.pk == self.instance.pk:
            self.add_error("parent", "Categoria pai não pode ser a própria categoria.")

        return cleaned_data


class GoalForCategoryForm(forms.Form):
    """Formulario de meta mensal de reducao por categoria, em formato BR."""

    target_amount = BRDecimalField(
        label="Valor limite (R$)",
        max_digits=14,
        decimal_places=2,
        min_value=0,
    )
    month = forms.TypedChoiceField(
        label="Mês",
        choices=[(number, month_name(number)) for number in range(1, 13)],
        coerce=int,
    )
    year = BRIntegerField(label="Ano", min_value=2000, max_value=2100)

    def __init__(self, *args, **kwargs):
        """Define mes e ano iniciais a partir da data local."""

        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["month"].initial = today.month
        self.fields["year"].initial = today.year
