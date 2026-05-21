"""Tests dos models do app insights."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from categories.models import Category
from insights.models import IgnoredPattern, Insight


class InsightModelTests(TestCase):
    """Garante regras principais do model Insight."""

    def setUp(self):
        self.category = Category.objects.create(name="Alimentacao")

    def test_create_category_limit_insight(self):
        """Deve criar insight de limite vinculado a categoria."""

        insight = Insight(
            title="Limite sugerido para Alimentacao",
            message="Criar meta para acompanhar alimentacao.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            category=self.category,
            suggested_amount=Decimal("500.00"),
            source_key="category-limit:1:2026-05",
        )
        insight.full_clean()
        insight.save()

        self.assertEqual(insight.status, Insight.Status.PENDING)
        self.assertEqual(insight.category, self.category)

    def test_category_limit_requires_category(self):
        """Insight de limite por categoria deve exigir categoria vinculada."""

        insight = Insight(
            title="Limite sugerido",
            message="Criar meta.",
            insight_type=Insight.InsightType.CATEGORY_LIMIT,
            suggested_amount=Decimal("500.00"),
        )

        with self.assertRaises(ValidationError):
            insight.full_clean()

    def test_suggested_amount_must_be_positive_when_present(self):
        """Nao deve validar insight com valor sugerido zero ou negativo."""

        insight = Insight(
            title="Valor invalido",
            message="Sugestao com valor invalido.",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            suggested_amount=Decimal("0.00"),
        )

        with self.assertRaises(ValidationError):
            insight.full_clean()

    def test_str_returns_title_and_type(self):
        """O __str__ deve retornar titulo e tipo legivel."""

        insight = Insight(
            title="Habito recorrente",
            message="Sugestao de acompanhamento.",
            insight_type=Insight.InsightType.RECURRING_EXPENSE,
            suggested_amount=Decimal("100.00"),
        )

        self.assertEqual(str(insight), "Habito recorrente (Despesa Recorrente)")


class IgnoredPatternModelTests(TestCase):
    """Garante regras principais do model IgnoredPattern."""

    def test_create_ignored_pattern(self):
        """Deve criar padrao silenciado."""

        pattern = IgnoredPattern.objects.create(
            pattern_key="category-limit:1",
            reason="Nao quero sugestoes para essa categoria.",
        )

        self.assertEqual(str(pattern), "category-limit:1")

    def test_pattern_key_must_be_unique(self):
        """Nao deve permitir dois padroes silenciados com a mesma chave."""

        IgnoredPattern.objects.create(pattern_key="category-limit:1")

        with self.assertRaises(IntegrityError):
            IgnoredPattern.objects.create(pattern_key="category-limit:1")
