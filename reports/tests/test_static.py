"""Testes dos estaticos do relatorio: CSS da pagina e JS do grafico (spec 017, D3)."""

import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parent.parent.parent
CSS_PATH = ROOT / "static" / "css" / "pages" / "reports.css"
JS_PATH = ROOT / "static" / "js" / "dashboard.js"
TEMPLATE_PATH = ROOT / "reports" / "templates" / "reports" / "monthly_dashboard.html"

COLOR_LITERAL = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(|\boklab\(",
)


def read(path):
    return path.read_text(encoding="utf-8")


class ReportsCssTests(SimpleTestCase):
    def test_reports_css_exists_without_color_literals(self):
        self.assertTrue(CSS_PATH.exists())
        self.assertNotRegex(read(CSS_PATH), COLOR_LITERAL)

    def test_reports_css_uses_only_report_prefixed_classes(self):
        css = re.sub(r"/\*.*?\*/", "", read(CSS_PATH), flags=re.S)
        names = set()
        for selector in re.findall(r"([^{}]+)\{", css):
            if selector.strip().startswith("@"):
                continue
            names.update(re.findall(r"\.([A-Za-z_][\w-]*)", selector))
        self.assertTrue(names)
        self.assertEqual({n for n in names if not n.startswith("report-")}, set())

    def test_category_bar_is_lime_from_the_shared_progress_component(self):
        components = read(CSS_PATH.parent.parent / "components.css")
        rule = re.search(r"\.progress__bar\s*\{([^}]*)\}", components).group(1)

        self.assertIn("var(--color-action-primary)", rule)
        self.assertNotIn("progress__bar", read(CSS_PATH))

    def test_template_loads_page_css(self):
        self.assertIn("css/pages/reports.css", read(TEMPLATE_PATH))


class DashboardChartJsTests(SimpleTestCase):
    def setUp(self):
        self.source = read(JS_PATH)

    def test_chart_has_bars_only(self):
        self.assertNotIn('type: "line"', self.source)
        self.assertNotIn("balance.borderColor", self.source)
        self.assertNotIn("pointBackgroundColor", self.source)

    def test_balance_color_is_read_for_the_tooltip(self):
        self.assertIn("--chart-balance", self.source)
        self.assertIn("--chart-surface", self.source)
        self.assertIn("--chart-text", self.source)

    def test_tooltip_shows_balance_of_the_month(self):
        self.assertIn("payload.balance", self.source)
        self.assertIn("Saldo", self.source)
