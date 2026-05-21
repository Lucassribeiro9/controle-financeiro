"""Forms do app categories."""

from django import forms

from .models import Category


class CategoryForm(forms.ModelForm):
    """Formulario para cadastrar e editar categorias."""

    class Meta:
        model = Category
        fields = ["name", "parent", "is_active"]
        labels = {
            "name": "Nome",
            "parent": "Categoria pai",
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
                self.add_error("name", "Ja existe uma categoria com este nome.")

        if self.instance.pk and parent and parent.pk == self.instance.pk:
            self.add_error("parent", "Categoria pai nao pode ser a propria categoria.")

        return cleaned_data
