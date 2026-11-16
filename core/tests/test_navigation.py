"""Testes da navegação principal: sidebar, barra inferior e folha "Mais" (spec 017, 3.2)."""

import re

from core.templatetags.navigation import nav_state
from core.testing import AuthenticatedTestCase
from django.contrib.auth import get_user_model
from django.template import Context
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import resolve, reverse

SIDEBAR_HREFS = [
    "/",
    "/transactions/",
    "/cards/statements/",
    "/reports/month/",
    "/goals/",
    "/accounts/",
    "/cards/",
    "/transactions/transfers/",
    "/installments/",
    "/recurrences/month/page/",
    "/imports/review/page/",
    "/categories/",
    "/institutions/",
    "/insights/page/",
    "/admin/",
]
BAR_HREFS = ["/", "/transactions/", "/transactions/create/", "/cards/statements/"]
SHEET_HREFS = [
    "/reports/month/",
    "/goals/",
    "/accounts/",
    "/cards/",
    "/transactions/transfers/",
    "/installments/",
    "/recurrences/month/page/",
    "/imports/review/page/",
    "/categories/",
    "/institutions/",
    "/insights/page/",
    "/admin/",
]


def region(html, pattern):
    match = re.search(pattern, html, re.S)
    assert match, f"trecho não encontrado: {pattern}"
    return match.group(0)


def sidebar(html):
    return region(html, r'<aside class="sidebar".*?</aside>')


def bottom_nav(html):
    return region(html, r'<nav class="bottom-nav".*?</nav>')


def more_sheet(html):
    return region(html, r'<div id="more-sheet".*?(?=<script|</body>)')


def hrefs(fragment):
    return re.findall(r'<a [^>]*href="([^"]+)"', fragment)


def current_hrefs(fragment):
    return re.findall(r'<a [^>]*href="([^"]+)"[^>]*aria-current="page"', fragment)


class NavStateTagTests(SimpleTestCase):
    """A seção ativa vem de namespace e path, sem consulta ao banco."""

    def state(self, path):
        request = RequestFactory().get(path)
        try:
            request.resolver_match = resolve(path)
        except Exception:
            request.resolver_match = None
        return nav_state(Context({"request": request}))

    def test_sections_by_namespace_and_path(self):
        cases = {
            "/": ("home", False),
            "/transactions/": ("transactions", False),
            "/transactions/create/": ("transactions", False),
            "/transactions/transfers/": ("transfers", True),
            "/transactions/transfers/create/": ("transfers", True),
            "/cards/statements/": ("statements", False),
            "/cards/": ("cards", True),
            "/cards/create/": ("cards", True),
            "/reports/month/": ("reports", True),
            "/goals/": ("goals", True),
            "/accounts/": ("accounts", True),
            "/installments/": ("installments", True),
            "/recurrences/month/page/": ("recurrences", True),
            "/imports/review/page/": ("imports", True),
            "/categories/": ("categories", True),
            "/institutions/": ("institutions", True),
            "/insights/page/": ("insights", True),
            "/admin/": ("admin", True),
        }
        for path, (section, in_more) in cases.items():
            with self.subTest(path=path):
                state = self.state(path)
                self.assertEqual(state["section"], section)
                self.assertEqual(state["in_more"], in_more)

    def test_unknown_path_has_no_section(self):
        state = self.state("/nao-existe/")

        self.assertEqual(state["section"], "")
        self.assertFalse(state["in_more"])


class SidebarTests(AuthenticatedTestCase):
    def get_sidebar(self, url="core:home"):
        response = self.client.get(reverse(url))
        self.assertEqual(response.status_code, 200)
        return sidebar(response.content.decode())

    def test_groups_and_links_in_order(self):
        html = self.get_sidebar()

        self.assertEqual(hrefs(html)[1:], SIDEBAR_HREFS)
        self.assertIn('aria-label="Principal"', html)
        self.assertIn(">Dinheiro<", html)
        self.assertIn(">Dados<", html)
        self.assertNotIn("Operação", html)
        self.assertNotIn("Dashboard", html)

    def test_relatorio_label_keeps_the_url(self):
        html = self.get_sidebar()

        self.assertRegex(html, r'<a [^>]*href="/reports/month/"[^>]*>\s*Relatório\s*</a>')

    def test_sidebar_has_no_icons(self):
        self.assertNotIn("<svg", self.get_sidebar())

    def test_active_item_by_namespace(self):
        cases = {
            "core:home": "/",
            "transactions:list": "/transactions/",
            "transactions:create": "/transactions/",
            "transactions:transfers": "/transactions/transfers/",
            "cards:statements": "/cards/statements/",
            "cards:list": "/cards/",
            "reports:monthly-dashboard-page": "/reports/month/",
            "goals:list": "/goals/",
            "accounts:list": "/accounts/",
            "categories:list": "/categories/",
            "institutions:list": "/institutions/",
        }
        for name, expected in cases.items():
            with self.subTest(route=name):
                self.assertEqual(current_hrefs(self.get_sidebar(name)), [expected])

    def test_footer_has_theme_switch_admin_and_logout_post(self):
        html = self.get_sidebar()

        self.assertIn('class="theme-switch', html)
        self.assertRegex(html, r'<a [^>]*href="/admin/"')
        self.assertRegex(html, r'<form [^>]*method="post"[^>]*action="/logout/"')
        self.assertIn("csrfmiddlewaretoken", html)
        self.assertIn("Sair", html)


class BottomNavTests(AuthenticatedTestCase):
    def get_html(self, url="core:home"):
        response = self.client.get(reverse(url))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_items_in_order(self):
        html = bottom_nav(self.get_html())

        self.assertEqual(hrefs(html), BAR_HREFS)
        self.assertRegex(html, r'<a [^>]*href="/transactions/create/"[^>]*aria-label="Novo lançamento"')
        self.assertIn(">Início<", html)
        self.assertIn(">Lançamentos<", html)
        self.assertIn(">Faturas<", html)
        self.assertIn(">Mais<", html)

    def test_mais_is_a_button_that_controls_the_sheet(self):
        html = bottom_nav(self.get_html())

        self.assertRegex(
            html,
            r'<button [^>]*type="button"[^>]*popovertarget="more-sheet"[^>]*aria-expanded="false"[^>]*>',
        )

    def test_icons_are_decorative(self):
        html = bottom_nav(self.get_html())

        self.assertEqual(html.count("<svg"), 5)
        self.assertEqual(html.count('aria-hidden="true"'), 5)

    def test_active_item_by_namespace(self):
        cases = {
            "core:home": "/",
            "transactions:list": "/transactions/",
            "transactions:create": "/transactions/",
            "cards:statements": "/cards/statements/",
        }
        for name, expected in cases.items():
            with self.subTest(route=name):
                self.assertEqual(current_hrefs(bottom_nav(self.get_html(name))), [expected])

    def test_new_transaction_button_is_never_current(self):
        html = bottom_nav(self.get_html("transactions:create"))

        self.assertNotRegex(html, r'href="/transactions/create/"[^>]*aria-current')

    def test_mais_is_marked_when_current_screen_is_in_the_sheet(self):
        in_sheet = bottom_nav(self.get_html("reports:monthly-dashboard-page"))
        on_bar = bottom_nav(self.get_html("core:home"))

        self.assertEqual(current_hrefs(in_sheet), [])
        self.assertRegex(in_sheet, r'<button [^>]*popovertarget="more-sheet"[^>]*aria-current="true"')
        self.assertNotIn('aria-current="true"', on_bar)


class MoreSheetTests(AuthenticatedTestCase):
    def get_html(self, url="core:home"):
        response = self.client.get(reverse(url))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_sheet_is_a_popover_with_the_remaining_screens(self):
        html = more_sheet(self.get_html())

        self.assertRegex(html, r'<div id="more-sheet" class="more-sheet" popover[ >]')
        self.assertEqual(hrefs(html), SHEET_HREFS)

    def test_sheet_does_not_repeat_the_bar_items(self):
        html = more_sheet(self.get_html())

        for href in ("/", "/transactions/", "/cards/statements/"):
            with self.subTest(href=href):
                self.assertNotIn(f'href="{href}"', html)

    def test_sheet_groups_and_labels(self):
        html = more_sheet(self.get_html())

        for label in ("Relatório", "Objetivos", "Dinheiro", "Dados", "Sistema", "Admin", "Sair"):
            with self.subTest(label=label):
                self.assertIn(label, html)
        self.assertNotIn("Dashboard", html)

    def test_sheet_has_theme_switch_and_logout_post(self):
        html = more_sheet(self.get_html())

        self.assertIn('class="theme-switch', html)
        self.assertRegex(html, r'<form [^>]*method="post"[^>]*action="/logout/"')
        self.assertIn("csrfmiddlewaretoken", html)

    def test_active_item_by_namespace(self):
        self.assertEqual(current_hrefs(more_sheet(self.get_html("reports:monthly-dashboard-page"))), ["/reports/month/"])
        self.assertEqual(
            current_hrefs(more_sheet(self.get_html("transactions:transfers"))),
            ["/transactions/transfers/"],
        )
        self.assertEqual(current_hrefs(more_sheet(self.get_html("core:home"))), [])


class ThemeSwitchTests(AuthenticatedTestCase):
    def test_three_buttons_hidden_until_js_and_without_id_or_name(self):
        html = self.client.get(reverse("core:home")).content.decode()
        switches = re.findall(r'<div class="theme-switch.*?</div>', html, re.S)

        self.assertEqual(len(switches), 2)
        for switch in switches:
            with self.subTest(switch=switch[:60]):
                self.assertIn("segmented", switch)
                self.assertIn("hidden", switch.split(">")[0])
                self.assertIn('role="group"', switch.split(">")[0])
                self.assertEqual(switch.count("<button"), 3)
                self.assertEqual(switch.count('aria-pressed="false"'), 3)
                for choice in ("light", "dark", "system"):
                    self.assertIn(f'data-theme-choice="{choice}"', switch)
                for label in ("Claro", "Escuro", "Sistema"):
                    self.assertIn(f">{label}<", switch)
                self.assertNotRegex(switch, r'\sid="|\sname="')


class LoginPageNavigationTests(TestCase):
    def test_login_has_only_the_brand(self):
        get_user_model().objects.create_user(username="lucas", password="x")
        html = self.client.get(reverse("login")).content.decode()

        self.assertIn('class="brand-mark"', html)
        for marker in ("sidebar", "bottom-nav", "more-sheet", "theme-switch", "nav-item"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, html)


class RatesModuleRemovedTests(AuthenticatedTestCase):
    """Garante que o módulo de Rendimentos (#196) foi descontinuado."""

    def test_rates_route_returns_404(self):
        response = self.client.get("/rates/")

        self.assertEqual(response.status_code, 404)

    def test_navigation_does_not_link_to_rates(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Rendimentos")
        self.assertNotContains(response, 'href="/rates/"')
