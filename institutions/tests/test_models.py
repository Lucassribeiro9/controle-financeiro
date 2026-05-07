"""Tests dos models do app institutions."""

from django.db import IntegrityError
from django.test import TestCase

from institutions.models import Institution


class InstitutionModelTests(TestCase):
    """Garante as regras principais do model Institution."""

    def test_create_institution_with_required_fields(self):
        """Deve criar instituição com os campos obrigatórios."""
        institution = Institution.objects.create(name="Itaú", code="341")

        self.assertEqual(institution.name, "Itaú")
        self.assertEqual(institution.code, "341")
        self.assertTrue(institution.is_active)

    def test_str_returns_name(self):
        """O __str__ deve retornar o nome amigável da instituição."""
        institution = Institution.objects.create(name="Nubank")
        self.assertEqual(str(institution), "Nubank")

    def test_name_must_be_unique(self):
        """Não deve permitir duas instituições com o mesmo nome."""
        Institution.objects.create(name="Inter")

        with self.assertRaises(IntegrityError):
            Institution.objects.create(name="Inter")
