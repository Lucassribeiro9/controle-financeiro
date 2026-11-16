from django.contrib import messages as django_messages
from django.contrib.messages.storage.base import Message
from django.template import Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase


FIELDS = Template('<input name="campo-de-teste">')


class StatusBadgePartialTests(SimpleTestCase):
    """Testes de renderização do partial status_badge."""

    def test_render_with_status_value(self):
        context = {"status": "paid"}
        html = render_to_string("partials/status_badge.html", context)

        self.assertIn('class="status status--positive"', html)
        self.assertIn("paid", html)

    def test_render_with_label(self):
        context = {"status": "pending", "label": "Aguardando"}
        html = render_to_string("partials/status_badge.html", context)

        self.assertIn('class="status status--warning"', html)
        self.assertIn("Aguardando", html)
        self.assertNotIn("pending", html)

    def test_render_with_unknown_status(self):
        context = {"status": "unknown_state"}
        html = render_to_string("partials/status_badge.html", context)

        self.assertIn('class="status status--neutral"', html)
        self.assertIn("unknown_state", html)

    def test_render_with_negative_status(self):
        html = render_to_string("partials/status_badge.html", {"status": "late"})

        self.assertIn('class="status status--negative"', html)

    def test_render_does_not_use_legacy_badge_classes(self):
        html = render_to_string("partials/status_badge.html", {"status": "paid"})

        self.assertNotIn("badge", html)


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

        self.assertIn('class="empty"', html)
        self.assertIn("Sem dados", html)
        self.assertIn("Nenhum item encontrado.", html)
        self.assertIn('href="/add/"', html)
        self.assertIn('class="btn btn--secondary"', html)
        self.assertIn("Adicionar", html)

    def test_render_without_cta(self):
        context = {
            "title": "Sem alertas",
            "description": "Tudo certo."
        }
        html = render_to_string("partials/empty_state.html", context)

        self.assertIn("Sem alertas", html)
        self.assertIn("Tudo certo.", html)
        self.assertNotIn("btn", html)

    def test_render_does_not_use_legacy_classes(self):
        html = render_to_string("partials/empty_state.html", {"title": "x", "description": "y"})

        self.assertNotIn("home-empty-action", html)


class FilterBarPartialTests(SimpleTestCase):
    """Testes de renderização do partial filter_bar."""

    def test_render_with_clear_url(self):
        context = {
            "clear_url": "/clear/",
        }
        html = render_to_string("partials/filter_bar.html", context)

        self.assertIn('href="/clear/"', html)
        self.assertIn("Limpar filtros", html)
        self.assertIn('type="submit"', html)

    def test_render_without_clear_url(self):
        context = {}
        html = render_to_string("partials/filter_bar.html", context)

        self.assertNotIn("Limpar filtros", html)
        self.assertNotIn('href="/clear/"', html)
        self.assertIn('type="submit"', html)

    def test_without_fields_template_renders_only_the_actions(self):
        html = render_to_string("partials/filter_bar.html", {"clear_url": "/clear/"})

        self.assertNotIn("<details", html)
        self.assertNotIn("<summary", html)
        self.assertIn("btn btn--primary", html)
        self.assertIn("btn btn--secondary", html)
        self.assertNotIn("style=", html)

    def test_with_fields_template_renders_collapsible_details(self):
        context = {
            "fields_template": FIELDS,
            "active_count": 2,
            "clear_url": "/clear/",
        }
        html = render_to_string("partials/filter_bar.html", context)

        self.assertIn('<details class="filters"', html)
        self.assertIn("<summary", html)
        self.assertIn("Filtros (2 ativos)", html)
        self.assertIn('name="campo-de-teste"', html)
        self.assertIn('href="/clear/"', html)
        self.assertIn('type="submit"', html)
        self.assertNotIn(" open", html)

    def test_summary_without_active_filters_has_no_count(self):
        context = {"fields_template": FIELDS, "active_count": 0}
        html = render_to_string("partials/filter_bar.html", context)

        self.assertIn(">Filtros</", html.replace("\n", "").replace("  ", ""))
        self.assertNotIn("ativo", html)

    def test_summary_singular_for_one_active_filter(self):
        context = {"fields_template": FIELDS, "active_count": 1}
        html = render_to_string("partials/filter_bar.html", context)

        self.assertIn("Filtros (1 ativo)", html)


class MessagesPartialTests(SimpleTestCase):
    """Testes de renderização do partial messages."""

    def render(self, level, text):
        return render_to_string("partials/messages.html", {"messages": [Message(level, text)]})

    def test_uses_alert_component_with_variant(self):
        html = self.render(django_messages.SUCCESS, "Salvo")

        self.assertIn("alert alert--success", html)
        self.assertIn("Salvo", html)
        self.assertNotIn('class="app-message ', html)

    def test_keeps_live_region(self):
        html = self.render(django_messages.ERROR, "Erro")

        self.assertIn('aria-live="polite"', html)
        self.assertIn("alert alert--error", html)
