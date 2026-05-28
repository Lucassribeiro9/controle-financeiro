"""Testes das views do app core."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    """Garante que a home consome o contexto operacional."""

    def test_home_renders_with_empty_database(self):
        """A home deve renderizar sem excecao quando nao ha dados financeiros."""

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_home_context_includes_operational_contract(self):
        """A view deve expor as chaves principais retornadas pelo selector."""

        response = self.client.get(reverse("core:home"))

        for key in [
            "summary",
            "alerts",
            "pending_items",
            "quick_actions",
            "empty_states",
        ]:
            self.assertIn(key, response.context)

        self.assertEqual(
            response.context["summary"]["realized"]["income"],
            Decimal("0.00"),
        )
        self.assertEqual(response.context["alerts"], [])
        self.assertEqual(response.context["pending_items"], [])
        self.assertTrue(response.context["empty_states"]["summary"]["is_empty"])
