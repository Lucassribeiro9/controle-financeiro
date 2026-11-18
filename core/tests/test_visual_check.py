"""scripts/visual_check.py: a comparacao de redirecionamento ignora a query string."""

import importlib.util
from pathlib import Path

from django.test import SimpleTestCase

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "visual_check.py"


def load_script():
    spec = importlib.util.spec_from_file_location("visual_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RedirectedTests(SimpleTestCase):
    def setUp(self):
        try:
            self.redirected = load_script().redirected
        except ImportError:
            self.skipTest("playwright nao instalado")

    def test_same_path_with_query_is_not_a_redirect(self):
        self.assertFalse(self.redirected("/transactions/?month=2026-11&type=expense", "/transactions/"))

    def test_plain_url_staying_put_is_not_a_redirect(self):
        self.assertFalse(self.redirected("/accounts/", "/accounts/"))

    def test_different_path_is_a_redirect(self):
        self.assertTrue(self.redirected("/transactions/?month=2026-11", "/login/"))

    def test_login_url_is_never_reported(self):
        self.assertFalse(self.redirected("/login/", "/"))
