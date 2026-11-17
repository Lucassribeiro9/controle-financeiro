"""Guarda de R-20 (spec 017, 3.9): classes do antigo static/css/app.css, removido na 3.9.

O arquivo nao existe mais. A lista abaixo e a copia congelada dos nomes de classe que ele
definia. Um template so pode usar um destes nomes se algum CSS novo (tokens, base,
components, layout ou pages/<app>.css) o define.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CSS_DIR = ROOT / "static" / "css"
SKIPPED_DIRS = {
    "docs", "venv", ".agents", ".claude", ".git", ".kilo", ".visual-check", "staticfiles",
    "node_modules",
}

LEGACY_CLASS_NAMES = frozenset(
    {
    "action-row", "active", "app-brand", "app-brand-mark", "app-main", "app-message",
    "app-messages", "app-nav", "app-nav-group", "app-nav-group-admin", "app-nav-group-label",
    "app-nav-link", "app-shell", "app-sidebar", "badge", "badge-danger", "badge-info",
    "badge-neutral", "badge-success", "badge-warning", "bulk-action-bar", "bulk-select-row",
    "button", "button-danger", "button-neutral", "button-secondary", "card-title-row",
    "cell-amount", "cell-code", "cell-count", "cell-date", "cell-period", "cell-primary",
    "cell-secondary", "cell-status", "cell-type", "chart-canvas-wrap", "chart-panel",
    "checkbox-row", "composition-copy", "composition-item", "composition-list",
    "dashboard-grid", "data-table", "detail-list", "detail-list-compact", "donut-meter",
    "expense", "field-error", "filter-bar", "forecast-card", "form-field", "form-grid",
    "goal-card", "home-alert-card", "home-alert-card-high", "home-alert-list",
    "home-alert-value", "home-alerts", "home-empty-action", "home-empty-note", "home-overview",
    "home-overview-header", "home-pending", "home-pending-card", "home-pending-count",
    "home-pending-grid", "home-quick-actions", "home-section-header", "home-summary-card",
    "home-summary-card-link", "home-summary-cta", "home-summary-grid", "import-card",
    "import-edit-details", "import-edit-form", "import-filter-bar", "import-summary-list",
    "income", "inline-form", "insight-alert", "insight-card", "is-active", "item-list",
    "limit-bar", "limit-bar-fill", "limit-bar-over", "menu-icon", "metric-card", "mobile-brand",
    "mobile-menu", "mobile-nav-panel", "mobile-topbar", "muted", "nav-icon",
    "nav-logout-button", "nav-logout-form", "notes-block", "page-header", "page-section",
    "pagination", "panel", "panel-title-row", "period-form", "review-tab", "review-tab-count",
    "review-tabs", "segment-control", "shortcut-card", "shortcut-grid", "sr-only",
    "summary-detail-balance", "summary-detail-section", "summary-grid", "surface-card",
    "table-responsive", "table-responsive-wide", "tag", "text-break", "text-nowrap",
    "text-right",
    }
)

_TEMPLATE_TAG = re.compile(r"\{%.*?%\}|\{\{.*?\}\}|\{#.*?#\}", re.S)


def css_class_names(css):
    """Nomes de classe usados em seletores (ignora comentarios e at-rules)."""

    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    names = set()
    for selector in re.findall(r"([^{}]+)\{", stripped):
        if selector.strip().startswith("@"):
            continue
        names.update(re.findall(r"\.([A-Za-z_][\w-]*)", selector))
    return names


def new_css_class_names():
    """Classes definidas pelo CSS vigente (tudo em static/css)."""

    names = set()
    for path in CSS_DIR.rglob("*.css"):
        names |= css_class_names(path.read_text(encoding="utf-8"))
    return names


def template_class_tokens(source):
    """Classes literais dos atributos class=. Descarta fragmentos colados a tag de template."""

    source = re.sub(r"\{#.*?#\}", "", source, flags=re.S)
    tokens = set()
    for value in re.findall(r'class="([^"]*)"', source):
        value = _TEMPLATE_TAG.sub("\0", value)
        tokens.update(token for token in value.split() if "\0" not in token)
    return tokens


def project_templates():
    for path in ROOT.rglob("*.html"):
        if SKIPPED_DIRS & set(path.relative_to(ROOT).parts):
            continue
        yield path
