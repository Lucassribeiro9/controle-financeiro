"""Tests das views do app categories."""

from django.test import TestCase
from django.urls import reverse

from categories.models import Category


class CategoryViewTests(TestCase):
    """Garante telas de listagem, criacao e edicao de categorias."""

    def test_category_list_page_returns_success(self):
        """Deve renderizar a lista de categorias."""

        Category.objects.create(name="Alimentacao")

        response = self.client.get(reverse("categories:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/list.html")
        self.assertContains(response, "Alimentacao")
        self.assertContains(response, "Categoria raiz")
        self.assertContains(response, "Ativa")

    def test_category_list_page_shows_children_count(self):
        """Deve exibir quantidade de subcategorias."""

        parent = Category.objects.create(name="Moradia")
        Category.objects.create(name="Aluguel", parent=parent)
        Category.objects.create(name="Condominio", parent=parent)

        response = self.client.get(reverse("categories:list"))

        parent_summary = next(
            category
            for category in response.context["categories"]
            if category.name == "Moradia"
        )
        self.assertEqual(parent_summary.children_count, 2)
        self.assertContains(response, "Moradia")

    def test_category_create_page_returns_form(self):
        """Deve renderizar formulario de criacao."""

        response = self.client.get(reverse("categories:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/form.html")
        self.assertContains(response, "Nova categoria")

    def test_post_create_root_category(self):
        """Deve criar categoria raiz."""

        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "Alimentacao",
                "parent": "",
                "is_active": "on",
            },
        )
        category = Category.objects.get(name="Alimentacao")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("categories:list"))
        self.assertIsNone(category.parent)
        self.assertTrue(category.is_active)

    def test_post_create_child_category(self):
        """Deve criar subcategoria vinculada a categoria pai."""

        parent = Category.objects.create(name="Moradia")

        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "Aluguel",
                "parent": parent.id,
                "is_active": "on",
            },
        )
        category = Category.objects.get(name="Aluguel")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(category.parent, parent)

    def test_post_update_category_edits_category(self):
        """Deve editar uma categoria."""

        parent = Category.objects.create(name="Casa")
        category = Category.objects.create(name="Aluguel")

        response = self.client.post(
            reverse("categories:update", kwargs={"category_id": category.id}),
            data={
                "name": "Moradia fixa",
                "parent": parent.id,
            },
        )
        category.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(category.name, "Moradia fixa")
        self.assertEqual(category.parent, parent)
        self.assertFalse(category.is_active)

    def test_post_duplicate_name_shows_form_error(self):
        """Deve impedir nome duplicado."""

        Category.objects.create(name="Transporte")

        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "transporte",
                "parent": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/form.html")
        self.assertContains(response, "Ja existe uma categoria com este nome.")
        self.assertEqual(Category.objects.count(), 1)
