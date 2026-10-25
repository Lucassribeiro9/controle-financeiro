"""Testes das regras globais do CSS que o JS da interface pressupoe."""

import re
from pathlib import Path

from django.test import SimpleTestCase

CSS_PATH = Path(__file__).resolve().parent.parent.parent / "static" / "css" / "app.css"


class HiddenAttributeCssTests(SimpleTestCase):
    """Garante que o atributo hidden esconde o elemento mesmo com display proprio."""

    def test_hidden_attribute_forces_display_none(self):
        """app.js usa hidden nos campos condicionais; o CSS nao pode anular isso."""

        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertRegex(
            css,
            re.compile(r"^\[hidden\]\s*\{[^}]*display:\s*none\s*!important;", re.M),
        )
