"""Testes da marcacao e do CSS do Inicio no visual novo (spec 017, item 3.3)."""

import re
from datetime import date, timedelta
from decimal import Decimal
from html.parser import HTMLParser

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from categories.models import Category
from core.testing import AuthenticatedTestCase
from core.tests.test_static_css import COLOR_LITERAL, CSS_DIR, class_names, read
from goals.models import Goal, MonthlyGoal
from institutions.models import Institution
from transactions.models import Transaction

HOME_CSS = CSS_DIR / "pages" / "home.css"
CARDS = ("realized", "pending", "forecasted")

# Classes legadas que so o partial transaction_table (dono: item 3.4, #293) ainda
# emite dentro do detalhe do resumo. Sai desta lista quando a 3.4 migrar o partial.
LEGACY_TRANSACTION_TABLE_CLASSES = {
    "table-responsive",
    "table-responsive-wide",
    "data-table",
    "cell-primary",
    "cell-date",
    "cell-type",
    "cell-status",
    "cell-secondary",
    "cell-amount",
    "muted",
}

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}


class Element:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = []

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


class TreeBuilder(HTMLParser):
    """Monta uma arvore minima de elementos (stdlib, sem dependencia nova)."""

    def __init__(self):
        super().__init__()
        self.root = Element("[document]", [], None)
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs, self.current)
        self.current.children.append(element)
        if tag not in VOID_TAGS:
            self.current = element

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data):
        self.current.text.append(data)


def parse(html):
    builder = TreeBuilder()
    builder.feed(html)
    return builder.root


def main_content(root):
    return next(el for el in root.walk() if el.tag == "main")


def money_text_classes():
    """Classes cuja regra pinta o texto com as cores de despesa (R-18)."""

    names = set()
    for path in (CSS_DIR / "components.css", HOME_CSS):
        css = re.sub(r"/\*.*?\*/", "", read(path), flags=re.S)
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            if re.search(r"(?<![-\w])color:\s*var\(--color-money-expense", body):
                names.update(re.findall(r"\.([A-Za-z_][\w-]*)", selector.split(",")[-1].split()[-1]))
    return names


class HomeFixtureMixin:
    def create_data(self):
        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            date=date.today(),
        )
        category = Category.objects.create(name="Lazer")
        goal = Goal.objects.create(
            name="Limite Lazer",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date.today(),
            category=category,
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=date.today().year,
            month=date.today().month,
            target_amount=Decimal("500.00"),
        )
        self.create_expense(account, category, "Cinema", "410.00")
        return account, category

    def create_expense(self, account, category, description, amount):
        return Transaction.objects.create(
            description=description,
            amount=Decimal(amount),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            category=category,
            date=date.today(),
        )


class HomeSmokeTests(HomeFixtureMixin, AuthenticatedTestCase):
    def test_home_renders_with_empty_database(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum lancamento neste mes")

    def test_home_renders_with_data(self):
        self.create_data()

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lazer")
        self.assertContains(response, "R$ 5.000,00")

    def test_title_and_greeting_use_first_name_or_username(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "<title>Início - Controle Financeiro</title>", html=True)
        self.assertContains(response, "Olá, tester")

        self.user.first_name = "Lucas"
        self.user.save()
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Olá, Lucas")

    def test_home_loads_page_css_after_shell_css(self):
        response = self.client.get(reverse("core:home"))
        html = response.content.decode()

        self.assertIn("css/pages/home.css", html)
        self.assertGreater(html.index("css/pages/home.css"), html.index("css/layout.css"))

    def test_get_does_not_write(self):
        self.create_data()
        before = Transaction.objects.count()

        self.client.get(reverse("core:home"))

        self.assertEqual(Transaction.objects.count(), before)


class HomeSummarySwitchTests(AuthenticatedTestCase):
    def setUp(self):
        self.root = parse(self.client.get(reverse("core:home")).content.decode())
        self.main = main_content(self.root)

    def radios(self):
        return [el for el in self.main.walk() if el.tag == "input" and el.attrs.get("type") == "radio"]

    def test_three_radios_share_a_group_outside_any_form(self):
        radios = self.radios()

        self.assertEqual(len(radios), 3)
        self.assertEqual({el.attrs["name"] for el in radios}, {"home-summary-card"})
        for radio in radios:
            self.assertNotIn("form", [a.tag for a in radio.ancestors()])

    def test_realized_is_checked_by_default(self):
        checked = [el.attrs["id"] for el in self.radios() if "checked" in el.attrs]

        self.assertEqual(checked, ["home-summary-realized"])

    def test_every_radio_has_a_label_and_is_a_sibling_of_the_cards(self):
        labels = {el.attrs.get("for") for el in self.main.walk() if el.tag == "label"}
        cards = next(el for el in self.main.walk() if "home__cards" in el.classes)
        for radio in self.radios():
            self.assertIn(radio.attrs["id"], labels)
            self.assertIs(radio.parent, cards.parent)

    def test_group_has_an_accessible_name(self):
        fieldset = next(el for el in self.main.walk() if el.tag == "fieldset")
        legend = next(el for el in fieldset.walk() if el.tag == "legend")

        self.assertTrue("".join(legend.text).strip())

    def test_three_cards_always_in_html_linking_to_detail(self):
        cards = [el for el in self.main.walk() if "home__card" in el.classes]

        self.assertEqual(len(cards), 3)
        self.assertEqual(
            [el.attrs["href"] for el in cards],
            [reverse("core:summary_detail", args=[card]) for card in CARDS],
        )

    def test_switch_has_no_script_and_no_requests(self):
        html = self.client.get(reverse("core:home")).content.decode()
        main_html = html[html.index('<main'):html.index("</main>")]

        self.assertNotIn("<script", main_html)
        self.assertNotIn("<form", main_html)


class HomeMarkupTests(HomeFixtureMixin, AuthenticatedTestCase):
    def setUp(self):
        self.create_data()
        self.main = main_content(parse(self.client.get(reverse("core:home")).content.decode()))

    def test_priority_alert_is_marked_by_text_not_only_by_color(self):
        self.create_data_with_statement()
        main = main_content(parse(self.client.get(reverse("core:home")).content.decode()))

        high = [el for el in main.walk() if "Prioridade alta" in "".join(el.text)]
        self.assertTrue(high)
        self.assertIn("status--negative", high[0].classes)

    def create_data_with_statement(self):
        institution = Institution.objects.get(code="077")
        account = FinancialAccount.objects.get(name="Conta corrente")
        card = Card.objects.create(
            name="Inter Gold",
            institution=institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=10,
            payment_account=account,
        )
        today = timezone.localdate()
        CardStatement.objects.create(
            card=card,
            year=today.year,
            month=today.month,
            closed_amount=Decimal("700.00"),
            expected_amount=Decimal("700.00"),
            due_date=today + timedelta(days=5),
            closing_date=today,
            status=CardStatement.StatementStatus.OPEN,
            payment_account=account,
        )

    def test_limit_at_risk_has_text_status_and_progress(self):
        limits = [el for el in self.main.walk() if "home__limit" in el.classes]

        self.assertEqual(len(limits), 1)
        text = "".join(t for el in limits[0].walk() for t in el.text)
        self.assertIn("Lazer", text)
        self.assertIn("Em risco", text)
        self.assertIn("R$ 410,00 de R$ 500,00", " ".join(text.split()))
        self.assertTrue(any("progress" in el.classes for el in limits[0].walk()))

    def test_exceeded_limit_uses_over_progress_and_text(self):
        account = FinancialAccount.objects.get(name="Conta corrente")
        category = Category.objects.get(name="Lazer")
        self.create_expense(account, category, "Show", "200.00")

        main = main_content(parse(self.client.get(reverse("core:home")).content.decode()))
        limit = next(el for el in main.walk() if "home__limit" in el.classes)

        self.assertIn("Excedido", " ".join(t for el in limit.walk() for t in el.text))
        self.assertTrue(any("progress--over" in el.classes for el in limit.walk()))

    def test_shortcuts_are_secondary_buttons(self):
        section = next(el for el in self.main.walk() if "home__shortcuts" in el.classes)
        links = [el for el in section.walk() if el.tag == "a"]

        self.assertGreaterEqual(len(links), 4)
        for link in links:
            self.assertIn("btn--secondary", link.classes)

    def test_markup_uses_only_new_classes(self):
        """Sem classe do app.css na marcacao propria (spec 017, D1)."""

        allowed = class_names(read(CSS_DIR / "components.css"))
        self.assert_only_new_classes(self.client.get(reverse("core:home")).content.decode(), allowed)

    def assert_only_new_classes(self, html, allowed, extra=frozenset()):
        main = main_content(parse(html))
        for element in main.walk():
            if element is main:
                continue
            for name in element.classes:
                ok = name.startswith("home__") or name in allowed or name in extra
                self.assertTrue(ok, f"classe fora do sistema novo: {name} em <{element.tag}>")

    def test_expense_values_sit_inside_a_surface(self):
        """R-18: texto de despesa precisa de ancestral .card ou .balance-card."""

        money = money_text_classes()
        self.assertIn("balance-card__expense", money)
        checked = 0
        for element in self.main.walk():
            if money & set(element.classes):
                checked += 1
                ancestors = {c for a in element.ancestors() for c in a.classes}
                self.assertTrue(
                    ancestors & {"card", "balance-card"},
                    f"despesa fora de surface: {element.classes}",
                )
        self.assertGreater(checked, 0)


class SummaryDetailMarkupTests(HomeFixtureMixin, AuthenticatedTestCase):
    def test_detail_uses_new_classes_with_legacy_partial_allowlist(self):
        self.create_data()
        allowed = class_names(read(CSS_DIR / "components.css"))
        for card in CARDS:
            html = self.client.get(reverse("core:summary_detail", args=[card])).content.decode()
            main = main_content(parse(html))
            for element in main.walk():
                if element is main:
                    continue
                for name in element.classes:
                    ok = (
                        name.startswith("home__")
                        or name in allowed
                        or name in LEGACY_TRANSACTION_TABLE_CLASSES
                    )
                    self.assertTrue(ok, f"{card}: classe fora do sistema novo: {name}")

    def test_detail_totals_sit_inside_a_card_and_back_is_secondary(self):
        self.create_data()
        html = self.client.get(reverse("core:summary_detail", args=["realized"])).content.decode()
        root = parse(html)
        money = money_text_classes()
        for element in main_content(root).walk():
            if money & set(element.classes):
                ancestors = {c for a in element.ancestors() for c in a.classes}
                self.assertTrue(ancestors & {"card", "balance-card"})

        backs = [
            el
            for el in root.walk()
            if el.tag == "a" and el.attrs.get("href") == reverse("core:home") and "btn--secondary" in el.classes
        ]
        self.assertGreaterEqual(len(backs), 1)

    def test_detail_loads_home_css_and_declares_topbar_back(self):
        html = self.client.get(reverse("core:summary_detail", args=["pending"])).content.decode()
        topbar = html[html.index('class="topbar__actions"'):html.index('<div class="shell">')]

        self.assertIn("css/pages/home.css", html)
        self.assertIn(reverse("core:home"), topbar)


class HomeCssTests(SimpleTestCase):
    def test_file_exists_without_literals_or_imports(self):
        css = read(HOME_CSS)

        self.assertNotRegex(css, COLOR_LITERAL)
        self.assertNotIn("@import", css)

    def test_only_local_prefix_or_component_classes(self):
        css = read(HOME_CSS)
        components = class_names(read(CSS_DIR / "components.css"))
        legacy = class_names(read(CSS_DIR / "app.css"))

        for name in class_names(css):
            self.assertTrue(name.startswith("home__") or name in components, name)
            self.assertNotIn(name, legacy - components, name)

    def test_switch_is_pure_css_with_sibling_selector(self):
        css = read(HOME_CSS)

        self.assertRegex(css, r"#home-summary-pending:checked\s*~")
        self.assertRegex(css, r"#home-summary-forecasted:checked\s*~")
        self.assertIn("max-width: 767.98px", css)
        self.assertIn("min-width: 768px", css)
        self.assertIn("min-width: 1200px", css)
        self.assertIn("clamp(", css)
