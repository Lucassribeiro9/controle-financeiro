"""Garante que o codigo de producao nao usa a data do sistema (spec 013, DAT-03, ADR-012)."""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

FORBIDDEN = re.compile(r"\b(?:date\.today|datetime\.now|datetime\.today)\s*\(")
EXCLUDED_DIRS = {"tests", "migrations", "venv", ".venv", ".claude", ".git", "node_modules"}


class NoSystemDateTests(SimpleTestCase):
    """Varre os .py do projeto atras de `date.today()` e `datetime.now()`."""

    def test_production_code_does_not_use_system_date(self):
        offenders = []
        for path in Path(settings.BASE_DIR).rglob("*.py"):
            relative = path.relative_to(settings.BASE_DIR)
            if EXCLUDED_DIRS.intersection(relative.parts):
                continue
            for number, line in enumerate(path.read_text().splitlines(), start=1):
                if FORBIDDEN.search(line):
                    offenders.append(f"{relative}:{number}")

        self.assertEqual(offenders, [], "Use timezone.localdate()/localtime()/now().")
