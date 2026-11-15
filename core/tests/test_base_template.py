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
