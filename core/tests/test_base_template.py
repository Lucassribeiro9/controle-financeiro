"""Testes do <head> do base.html: tema sem flash, ordem dos CSS e preload."""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

BASE_TEMPLATE = Path(__file__).resolve().parent.parent.parent / "templates" / "base.html"


class BaseTemplateHeadTests(TestCase):
    """Usa a tela de login, que estende base.html sem exigir dados."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="lucas", password="x")

    def get_html(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def head(self, html):
        return re.search(r"<head>(.*?)</head>", html, re.S).group(1)

    def stylesheet_hrefs(self, html):
        return re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)

    def test_theme_script_comes_before_the_first_stylesheet(self):
        head = self.head(self.get_html())

        script = head.index("<script>")
        first_stylesheet = head.index('<link rel="stylesheet"')

        self.assertLess(script, first_stylesheet)
        self.assertIn("localStorage", head[script:first_stylesheet])
        self.assertIn("data-theme", head[script:first_stylesheet])

    def test_theme_script_has_no_cookie_or_request(self):
        head = self.head(self.get_html())
        inline = re.search(r"<script>(.*?)</script>", head, re.S).group(1)

        self.assertNotRegex(inline, r"cookie|fetch|XMLHttpRequest|sendBeacon")

    def test_server_html_has_no_data_theme_on_html_tag(self):
        html = self.get_html()

        self.assertNotRegex(html, r"<html[^>]*data-theme")

    def test_css_order(self):
        hrefs = self.stylesheet_hrefs(self.head(self.get_html()))
        names = [href.rsplit("/", 1)[-1] for href in hrefs]

        self.assertEqual(
            names[:5],
            ["tokens.css", "base.css", "app.css", "components.css", "layout.css"],
        )

    def test_page_css_block_comes_after_layout(self):
        source = (BASE_TEMPLATE).read_text(encoding="utf-8")

        self.assertLess(source.index("layout.css"), source.index("{% block page_css %}"))
        self.assertLess(source.index("{% block page_css %}"), source.index("</head>"))

    def test_theme_color_has_one_meta_per_theme(self):
        head = self.head(self.get_html())

        self.assertRegex(
            head,
            r'<meta name="theme-color" content="#e8ebe6" media="\(prefers-color-scheme: light\)">',
        )
        self.assertRegex(
            head,
            r'<meta name="theme-color" content="#171721" media="\(prefers-color-scheme: dark\)">',
        )

    def test_inter_is_preloaded_from_vendor(self):
        head = self.head(self.get_html())

        self.assertRegex(
            head,
            r'<link rel="preload" href="[^"]*vendor/inter/inter-latin-wght-normal[^"]*\.woff2" '
            r'as="font" type="font/woff2" crossorigin>',
        )

    def test_theme_js_is_loaded_deferred_in_head(self):
        head = self.head(self.get_html())

        self.assertRegex(head, r'<script src="[^"]*js/theme\.js" defer></script>')

    def test_no_external_hosts_in_head(self):
        head = self.head(self.get_html())

        self.assertNotRegex(head, r"https?://")

    def test_get_does_not_set_cookies_for_theme(self):
        response = self.client.get(reverse("login"))

        self.assertNotIn("theme", response.cookies)


class BaseTemplateBodyTests(TestCase):
    """Casca do <body> (spec 017, 3.2): topo, sidebar, main, barra inferior e blocos."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="lucas", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def get_html(self, url="core:home"):
        return self.client.get(reverse(url)).content.decode()

    def body(self, html):
        return re.search(r"<body[^>]*>(.*?)</body>", html, re.S).group(1)

    def render(self, template_source):
        from django.template import Context, Template
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = self.user
        return Template(template_source).render(Context({"request": request, "user": self.user}))

    def test_body_defaults_to_nav_mode(self):
        self.assertRegex(self.get_html(), r'<body class="shell-nav">')

    def test_shell_mode_block_becomes_body_class(self):
        html = self.render('{% extends "base.html" %}{% block shell_mode %}task{% endblock %}')

        self.assertRegex(html, r'<body class="shell-task">')

    def test_topbar_actions_block_renders_inside_the_topbar(self):
        html = self.render(
            '{% extends "base.html" %}{% block topbar_actions %}<b id="x">Nov/2026</b>{% endblock %}'
        )
        topbar = re.search(r'<header class="topbar".*?</header>', html, re.S).group(0)

        self.assertIn('<b id="x">Nov/2026</b>', topbar)

    def test_existing_blocks_stay_stable(self):
        source = BASE_TEMPLATE.read_text(encoding="utf-8")

        for block in ("title", "page_css", "content", "scripts"):
            with self.subTest(block=block):
                self.assertIn("{% block " + block + " %}", source)

    def test_skip_link_is_first_and_main_is_the_target(self):
        body = self.body(self.get_html()).lstrip()

        self.assertTrue(body.startswith('<a class="skip-link" href="#content">'))
        self.assertRegex(body, r'<main id="content" class="shell__main" tabindex="-1">')

    def test_shell_order_in_body(self):
        body = self.body(self.get_html())
        order = [
            body.index('class="topbar"'),
            body.index('class="sidebar"'),
            body.index('<main id="content"'),
            body.index('class="bottom-nav"'),
            body.index('id="more-sheet"'),
        ]

        self.assertEqual(order, sorted(order))

    def test_layout_js_is_deferred_after_theme_js(self):
        html = self.get_html()

        self.assertRegex(html, r'<script src="[^"]*js/layout\.js" defer></script>')
        self.assertLess(html.index("js/theme.js"), html.index("js/layout.js"))
        self.assertGreater(html.index("js/layout.js"), html.index("<body"))

    def test_anonymous_shell_has_only_brand_in_topbar(self):
        self.client.logout()
        html = self.get_html("login")
        topbar = re.search(r'<header class="topbar".*?</header>', html, re.S).group(0)

        self.assertIn("brand-mark", topbar)
        self.assertNotIn("<button", topbar)
        self.assertNotIn('class="bottom-nav"', html)
        self.assertNotIn("layout.js", html)

    def test_legacy_shell_classes_are_gone(self):
        html = self.get_html()

        for name in ("app-shell", "app-sidebar", "mobile-topbar", "mobile-menu", "app-nav-link"):
            with self.subTest(name=name):
                self.assertNotIn(name, html)
