"""Testes das regras globais do CSS e do JS que a interface pressupoe."""

import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "static"
CSS_DIR = STATIC / "css"
CSS_PATH = CSS_DIR / "app.css"
DESIGN_PATH = ROOT / "docs" / "design" / "DESIGN.md"

COLOR_LITERAL = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(|\boklab\(",
)
DARK_MEDIA_BLOCK = re.compile(
    r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*"
    r":root:not\(\[data-theme=\"light\"\]\)\s*\{(?P<body>[^}]*)\}\s*\}",
)
DARK_ATTRIBUTE_BLOCK = re.compile(
    r":root\[data-theme=\"dark\"\]\s*\{(?P<body>[^}]*)\}",
)
LIGHT_BLOCK = re.compile(r"^:root\s*\{(?P<body>[^}]*)\}", re.M)


def read(path):
    return path.read_text(encoding="utf-8")


def declarations(body):
    """Devolve {propriedade: valor} de um bloco de declaracoes."""

    result = {}
    for match in re.finditer(r"(--[\w-]+|[\w-]+)\s*:\s*([^;]+);", body):
        result[match.group(1)] = " ".join(match.group(2).split())
    return result


def design_color_tokens():
    """Le a tabela de cores do DESIGN.md: {--color-x: (claro, escuro)}."""

    tokens = {}
    row = re.compile(
        r"^\|\s*`(color/[\w/-]+)`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|\s*`(#[0-9a-fA-F]{6})`",
        re.M,
    )
    for match in row.finditer(read(DESIGN_PATH)):
        name = "--" + match.group(1).replace("/", "-")
        tokens[name] = (match.group(2).lower(), match.group(3).lower())
    return tokens


def class_names(css):
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    selectors = re.findall(r"([^{}]+)\{", stripped)
    names = set()
    for selector in selectors:
        if selector.strip().startswith("@"):
            continue
        names.update(re.findall(r"\.([A-Za-z_][\w-]*)", selector))
    return names


class HiddenAttributeCssTests(SimpleTestCase):
    """Garante que o atributo hidden esconde o elemento mesmo com display proprio."""

    hidden_rule = re.compile(r"^\[hidden\]\s*\{[^}]*display:\s*none\s*!important;", re.M)

    def test_hidden_attribute_forces_display_none(self):
        """app.js usa hidden nos campos condicionais; o CSS nao pode anular isso."""

        self.assertRegex(read(CSS_PATH), self.hidden_rule)

    def test_base_css_also_forces_hidden(self):
        self.assertRegex(read(CSS_DIR / "base.css"), self.hidden_rule)


class TokensCssTests(SimpleTestCase):
    """R-01: todas as cores do DESIGN.md nos dois temas."""

    def setUp(self):
        self.css = read(CSS_DIR / "tokens.css")
        self.light = declarations(LIGHT_BLOCK.search(self.css).group("body"))
        self.dark_media = declarations(DARK_MEDIA_BLOCK.search(self.css).group("body"))
        self.dark_attr = declarations(DARK_ATTRIBUTE_BLOCK.search(self.css).group("body"))

    def test_design_md_table_was_parsed(self):
        self.assertGreaterEqual(len(design_color_tokens()), 18)

    def test_light_theme_has_every_design_token(self):
        for name, (light, _dark) in design_color_tokens().items():
            with self.subTest(token=name):
                self.assertEqual(self.light.get(name, "").lower(), light)

    def test_dark_theme_has_every_design_token_in_both_selectors(self):
        for name, (_light, dark) in design_color_tokens().items():
            with self.subTest(token=name):
                self.assertEqual(self.dark_media.get(name, "").lower(), dark)
                self.assertEqual(self.dark_attr.get(name, "").lower(), dark)

    def test_dark_blocks_are_identical(self):
        self.assertEqual(self.dark_media, self.dark_attr)

    def test_color_scheme_follows_theme(self):
        self.assertEqual(self.light.get("color-scheme"), "light")
        self.assertEqual(self.dark_media.get("color-scheme"), "dark")
        self.assertEqual(self.dark_attr.get("color-scheme"), "dark")

    def test_chart_tokens_exist_in_both_themes(self):
        for name in (
            "--chart-income",
            "--chart-expense",
            "--chart-balance",
            "--chart-grid",
            "--chart-text",
            "--chart-surface",
        ):
            with self.subTest(token=name):
                self.assertIn(name, self.light)

    def test_chart_balance_changes_with_the_theme(self):
        self.assertEqual(self.light["--chart-balance"], "var(--color-text-primary)")
        self.assertEqual(self.dark_media["--chart-balance"], "var(--color-action-primary)")
        self.assertEqual(self.dark_attr["--chart-balance"], "var(--color-action-primary)")

    def test_typography_radius_and_space_tokens(self):
        for name in (
            "--font-sans",
            "--font-weight-display",
            "--radius-sm",
            "--radius-md",
            "--radius-lg",
            "--radius-xl",
            "--radius-pill",
            "--space-xs",
            "--space-3xl",
        ):
            with self.subTest(token=name):
                self.assertIn(name, self.light)
        self.assertEqual(self.light["--font-weight-display"], "800")
        self.assertEqual(self.dark_media["--font-weight-display"], "500")

    def test_no_shadow_token_has_elevation(self):
        self.assertNotRegex(self.css, r"box-shadow\s*:\s*[^n;]")


class BaseCssTests(SimpleTestCase):
    """R-05: Inter servida de static/vendor/inter."""

    def setUp(self):
        self.css = read(CSS_DIR / "base.css")

    def test_font_face_points_to_vendored_inter(self):
        self.assertIn("@font-face", self.css)
        self.assertIn("../vendor/inter/inter-latin-wght-normal.woff2", self.css)
        self.assertRegex(self.css, r"font-weight:\s*100\s+900")
        self.assertRegex(self.css, r"font-display:\s*swap")

    def test_vendored_inter_files_exist(self):
        self.assertTrue((STATIC / "vendor/inter/inter-latin-wght-normal.woff2").is_file())
        self.assertIn("SIL OPEN FONT LICENSE", read(STATIC / "vendor/inter/LICENSE").upper())

    def test_no_external_fonts_or_imports(self):
        self.assertNotIn("@import", self.css)
        self.assertNotRegex(self.css, r"https?://")

    def test_skip_link_and_focus_are_in_base(self):
        self.assertIn(".skip-link", self.css)
        self.assertIn(":focus-visible", self.css)

    def test_base_css_has_no_color_literals(self):
        self.assertNotRegex(self.css, COLOR_LITERAL)


class LegacyAppCssTests(SimpleTestCase):
    """R-08: o app.css legado so usa variaveis dos tokens."""

    def setUp(self):
        self.css = read(CSS_PATH)

    def test_app_css_has_no_color_literals(self):
        self.assertNotRegex(self.css, COLOR_LITERAL)

    def test_font_and_color_scheme_come_from_tokens(self):
        self.assertNotIn("Arial", self.css)
        self.assertNotIn("color-scheme", self.css)
        self.assertNotIn("font-family", self.css)

    def test_legacy_variables_alias_the_tokens(self):
        root = declarations(LIGHT_BLOCK.search(self.css).group("body"))
        self.assertEqual(root["--bg"], "var(--color-bg-canvas)")
        self.assertEqual(root["--surface"], "var(--color-bg-surface)")
        self.assertEqual(root["--text"], "var(--color-text-primary)")
        self.assertEqual(root["--line"], "var(--color-border-default)")

    def test_accent_background_and_text_use_are_separated(self):
        root = declarations(LIGHT_BLOCK.search(self.css).group("body"))
        self.assertEqual(root["--accent"], "var(--color-action-primary)")
        self.assertEqual(root["--accent-fg"], "var(--color-text-primary)")
        self.assertEqual(root["--accent-soft"], "var(--color-bg-brand-pale)")

    def test_sidebar_aliases_are_not_light_on_light(self):
        root = declarations(LIGHT_BLOCK.search(self.css).group("body"))
        self.assertEqual(root["--sidebar"], "var(--color-bg-surface)")
        self.assertEqual(root["--sidebar-active"], "var(--color-text-primary)")
        self.assertEqual(root["--sidebar-muted"], "var(--color-text-secondary)")

    def test_shadows_are_none(self):
        root = declarations(LIGHT_BLOCK.search(self.css).group("body"))
        self.assertEqual(root["--shadow"], "none")
        self.assertEqual(root["--shadow-subtle"], "none")

    def test_every_legacy_variable_name_still_exists(self):
        root = declarations(LIGHT_BLOCK.search(self.css).group("body"))
        legacy = {
            "--bg", "--sidebar", "--sidebar-muted", "--sidebar-active", "--surface",
            "--surface-muted", "--text", "--muted", "--line", "--accent",
            "--accent-soft", "--income", "--expense", "--success", "--success-soft",
            "--warning", "--warning-soft", "--danger", "--danger-soft", "--info",
            "--info-soft", "--neutral", "--neutral-soft", "--focus-ring", "--radius",
            "--space-1", "--space-2", "--space-3", "--space-4", "--space-5",
            "--space-6", "--space-8",
        }
        self.assertEqual(legacy - set(root), set())

    def test_every_variable_used_is_defined(self):
        defined = set()
        for name in ("tokens.css", "app.css", "base.css", "components.css"):
            defined.update(re.findall(r"(--[\w-]+)\s*:", read(CSS_DIR / name)))
        used = set()
        for template in ROOT.rglob("*.html"):
            if any(part in {"docs", "venv", ".agents", ".claude"} for part in template.parts):
                continue
            used.update(re.findall(r"var\((--[\w-]+)", read(template)))
        for name in ("app.css", "base.css", "components.css", "tokens.css"):
            used.update(re.findall(r"var\((--[\w-]+)", read(CSS_DIR / name)))
        # variaveis definidas inline pelo proprio template (--share, --share-color)
        used -= {"--share", "--share-color"}
        self.assertEqual(used - defined, set())


class ComponentsCssTests(SimpleTestCase):
    """Os componentes novos nao colidem com classes do app.css legado."""

    def setUp(self):
        self.css = read(CSS_DIR / "components.css")

    def test_defines_every_component_of_the_spec(self):
        names = class_names(self.css)
        for component in (
            "btn", "status", "card", "balance-card", "field", "alert", "segmented",
            "period-picker", "filters", "list-table", "summary-rows", "progress",
            "empty",
        ):
            with self.subTest(component=component):
                self.assertIn(component, names)

    def test_component_class_names_do_not_collide_with_legacy(self):
        self.assertEqual(class_names(self.css) & class_names(read(CSS_PATH)), set())

    def test_components_have_no_color_literals(self):
        self.assertNotRegex(self.css, COLOR_LITERAL)

    def test_status_has_the_four_variants(self):
        for variant in ("positive", "warning", "neutral", "negative"):
            self.assertIn(f".status--{variant}", self.css)

    def test_filters_open_on_desktop_without_javascript(self):
        self.assertIn("::details-content", self.css)
        self.assertIn("min-width: 768px", self.css)


class LayoutCssTests(SimpleTestCase):
    """3.2: casca do app (sidebar, topo, barra inferior, folha Mais) so com tokens."""

    def setUp(self):
        self.css = read(CSS_DIR / "layout.css")
        self.classes = class_names(self.css)

    def test_has_no_color_literals(self):
        self.assertNotRegex(re.sub(r"/\*.*?\*/", "", self.css, flags=re.S), COLOR_LITERAL)

    def test_defines_the_shell_classes(self):
        for name in (
            "shell",
            "shell__main",
            "topbar",
            "sidebar",
            "nav-item",
            "bottom-nav",
            "more-sheet",
            "theme-switch",
            "brand-mark",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.classes)

    def test_does_not_reuse_legacy_class_names(self):
        legacy = class_names(read(CSS_PATH))
        legacy_in_layout = {
            name for name in self.classes if name.startswith(("app-", "mobile-")) or name in legacy
        }
        self.assertEqual(legacy_in_layout, set())

    def test_desktop_is_declared_from_768px_up(self):
        self.assertIn("@media (min-width: 768px)", self.css)
        self.assertNotIn("@media (max-width", self.css)
        self.assertRegex(self.css, r"\.sidebar\s*\{[^}]*\b240px")

    def test_content_margins_are_16_and_40(self):
        self.assertIn("var(--space-lg)", self.css)
        self.assertRegex(self.css, r"\b40px\b")

    def test_bottom_inset_variable_uses_safe_area(self):
        self.assertIn("--shell-bottom-inset", self.css)
        self.assertIn("env(safe-area-inset-bottom", self.css)

    def test_task_mode_hides_topbar_and_bottom_nav_on_mobile(self):
        self.assertRegex(self.css, r"\.shell-task\s+\.bottom-nav")
        self.assertRegex(self.css, r"\.shell-task\s+\.topbar")

    def test_sheet_locks_scroll_and_respects_reduced_motion(self):
        self.assertIn(":has(", self.css)
        self.assertIn(":popover-open", self.css)
        self.assertIn("prefers-reduced-motion", self.css)


class LayoutScriptTests(SimpleTestCase):
    """3.2: layout.js so sincroniza o controle de tema e a folha; sem rede nem cookie."""

    forbidden = re.compile(r"document\.cookie|fetch\(|XMLHttpRequest|sendBeacon|WebSocket")

    def setUp(self):
        self.source = read(STATIC / "js" / "layout.js")

    def test_has_no_network_or_cookie(self):
        self.assertNotRegex(self.source, self.forbidden)

    def test_has_no_color_literals(self):
        self.assertNotRegex(self.source, COLOR_LITERAL)

    def test_syncs_theme_switch_with_theme_js(self):
        self.assertIn("window.Theme", self.source)
        self.assertIn("themechange", self.source)
        self.assertIn("data-theme-choice", self.source)
        self.assertIn("aria-pressed", self.source)

    def test_manages_the_sheet(self):
        self.assertIn("more-sheet", self.source)
        self.assertIn("toggle", self.source)
        self.assertIn("aria-expanded", self.source)
        self.assertIn("hidePopover", self.source)
        self.assertIn("min-width: 768px", self.source)


class ThemeScriptTests(SimpleTestCase):
    """R-04: trocar o tema nao faz requisicao nem grava cookie."""

    forbidden = re.compile(r"document\.cookie|fetch\(|XMLHttpRequest|sendBeacon|WebSocket")

    def test_theme_js_has_no_network_or_cookie(self):
        source = read(STATIC / "js" / "theme.js")
        self.assertNotRegex(source, self.forbidden)

    def test_theme_js_persists_in_local_storage_and_emits_event(self):
        source = read(STATIC / "js" / "theme.js")
        self.assertIn("localStorage", source)
        self.assertIn("themechange", source)
        self.assertIn("prefers-color-scheme", source)
        self.assertIn("matchMedia", source)


class DashboardJsTests(SimpleTestCase):
    """R-06: o grafico le as cores dos tokens e redesenha no themechange."""

    def setUp(self):
        self.source = read(STATIC / "js" / "dashboard.js")

    def test_dashboard_js_has_no_color_literals(self):
        self.assertNotRegex(self.source, COLOR_LITERAL)

    def test_dashboard_js_reads_chart_tokens(self):
        self.assertIn("getComputedStyle", self.source)
        for name in ("chart-income", "chart-expense", "chart-balance", "chart-grid", "chart-text"):
            self.assertIn(f"--{name}", self.source)

    def test_dashboard_js_redraws_on_themechange(self):
        self.assertIn('"themechange"', self.source)
        self.assertIn(".update(", self.source)
