from django.template.loader import render_to_string
from django.test import SimpleTestCase


class StatusBadgePartialTests(SimpleTestCase):
    """Testes de renderização do partial status_badge."""

    def test_render_with_status_value(self):
        context = {"status": "paid"}
        html = render_to_string("partials/status_badge.html", context)
        
        self.assertIn('class="badge badge-success"', html)
        self.assertIn("paid", html)

    def test_render_with_label(self):
        context = {"status": "pending", "label": "Aguardando"}
        html = render_to_string("partials/status_badge.html", context)
        
        self.assertIn('class="badge badge-warning"', html)
        self.assertIn("Aguardando", html)
        self.assertNotIn("pending", html)

    def test_render_with_unknown_status(self):
        context = {"status": "unknown_state"}
        html = render_to_string("partials/status_badge.html", context)
        
        self.assertIn('class="badge badge-neutral"', html)
        self.assertIn("unknown_state", html)


class EmptyStatePartialTests(SimpleTestCase):
    """Testes de renderização do partial empty_state."""

    def test_render_with_all_params(self):
        context = {
            "title": "Sem dados",
            "description": "Nenhum item encontrado.",
            "cta_label": "Adicionar",
            "cta_url": "/add/"
        }
        html = render_to_string("partials/empty_state.html", context)
        
        self.assertIn("Sem dados", html)
        self.assertIn("Nenhum item encontrado.", html)
        self.assertIn('href="/add/"', html)
        self.assertIn("Adicionar", html)

    def test_render_without_cta(self):
        context = {
            "title": "Sem alertas",
            "description": "Tudo certo."
        }
        html = render_to_string("partials/empty_state.html", context)
        
        self.assertIn("Sem alertas", html)
        self.assertIn("Tudo certo.", html)
        self.assertNotIn('class="button', html)
