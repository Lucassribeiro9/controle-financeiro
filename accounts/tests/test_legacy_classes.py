"""Guarda da remodelacao (spec 017, issue 297): sem classe do app.css nas telas de cadastro e login."""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES = [
    "accounts/templates/accounts/adjust_balance.html",
    "accounts/templates/accounts/detail.html",
    "accounts/templates/accounts/form.html",
    "accounts/templates/accounts/list.html",
    "categories/templates/categories/create_goal.html",
    "categories/templates/categories/form.html",
    "categories/templates/categories/list.html",
    "installments/templates/installments/confirm_cancellation.html",
    "installments/templates/installments/detail.html",
    "installments/templates/installments/form.html",
    "installments/templates/installments/list.html",
    "institutions/templates/institutions/form.html",
    "institutions/templates/institutions/list.html",
    "templates/registration/login.html",
]
PAGE_CSS = ["accounts", "categories", "institutions", "installments", "login"]


def selectors(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return set(re.findall(r"\.([a-zA-Z_][\w-]*)", css))


def template_classes(source):
    source = re.sub(r"\{#.*?#\}", "", source, flags=re.S)
    found = set()
    for value in re.findall(r'class="([^"]*)"', source):
        value = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", value)
        found.update(value.split())
    return found


class LegacyClassesTests(SimpleTestCase):
    def legacy(self):
        return selectors((ROOT / "static/css/app.css").read_text(encoding="utf-8"))

    def test_templates_use_no_class_from_app_css(self):
        legacy = self.legacy()
        for name in TEMPLATES:
            with self.subTest(template=name):
                used = template_classes((ROOT / name).read_text(encoding="utf-8"))
                self.assertEqual(used & legacy, set())

    def test_page_css_defines_no_selector_from_app_css(self):
        legacy = self.legacy()
        for name in PAGE_CSS:
            with self.subTest(css=name):
                path = ROOT / "static/css/pages" / f"{name}.css"
                self.assertTrue(path.exists())
                self.assertEqual(selectors(path.read_text(encoding="utf-8")) & legacy, set())

    def test_page_css_uses_only_tokens_for_color(self):
        for name in PAGE_CSS:
            with self.subTest(css=name):
                css = (ROOT / "static/css/pages" / f"{name}.css").read_text(encoding="utf-8")
                self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b|rgba?\(")


class LoginMarkupTests(TestCase):
    def test_login_uses_new_components_and_task_mode(self):
        html = self.client.get(reverse("login")).content.decode()

        self.assertContains_all(
            html,
            ["Entrar", "Entre para ver suas finanças", 'class="field', "btn btn--primary", "pages/login.css"],
        )
        self.assertNotIn("form-field", html)
        self.assertNotIn("app-message", html)

    def test_login_keeps_fields_used_by_visual_check(self):
        html = self.client.get(reverse("login")).content.decode()

        self.assertIn('name="username"', html)
        self.assertIn('name="password"', html)
        self.assertIn('type="submit"', html)

    def test_login_error_uses_alert_error(self):
        get_user_model().objects.create_user(username="lucas", password="certa-123456")

        response = self.client.post(reverse("login"), {"username": "lucas", "password": "errada"})

        self.assertContains(response, "alert alert--error")
        self.assertNotContains(response, "app-message")

    def test_login_template_declares_task_shell_mode(self):
        source = (ROOT / "templates/registration/login.html").read_text(encoding="utf-8")

        self.assertIn("{% block shell_mode %}task{% endblock %}", source)

    def assertContains_all(self, html, parts):
        for part in parts:
            self.assertIn(part, html)
