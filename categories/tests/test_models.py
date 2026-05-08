"""Tests dos models do app categories."""

from django.db import IntegrityError
from django.test import TestCase

from categories.models import Category


class CategoryModelTests(TestCase):
    """Garante as regras principais do model Category."""

    def test_create_category_with_required_fields(self):
        """Deve criar categoria com os campos obrigatorios."""
        category = Category.objects.create(name="Alimentacao")

        self.assertEqual(category.name, "Alimentacao")
        self.assertIsNone(category.parent)
        self.assertTrue(category.is_active)

    def test_str_returns_name(self):
        """O __str__ deve retornar o nome amigavel da categoria."""
        category = Category.objects.create(name="Transporte")
        self.assertEqual(str(category), "Transporte")

    def test_name_must_be_unique(self):
        """Nao deve permitir duas categorias com o mesmo nome."""
        Category.objects.create(name="Lazer")

        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Lazer")

    def test_can_create_parent_and_child_categories(self):
        """Deve permitir hierarquia simples de categoria pai e filha."""
        parent = Category.objects.create(name="Moradia")
        child = Category.objects.create(name="Aluguel", parent=parent)

        self.assertEqual(child.parent, parent)
