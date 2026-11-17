"""Testes dos templates de lancamentos no visual novo (spec 017, item 3.4, #293)."""

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.testing import AuthenticatedTestCase
from core.tests.legacy_css import LEGACY_CLASS_NAMES, new_css_class_names, template_class_tokens
from django.test import SimpleTestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction, Transfer
from transactions.services import create_transaction

ROOT = Path(__file__).resolve().parent.parent.parent
CSS_DIR = ROOT / "static" / "css"
PAGE_CSS = "css/pages/transactions.css"
TEMPLATE_FILES = [
    ROOT / "transactions" / "templates" / "transactions" / name
    for name in (
        "list.html",
        "_filtros.html",
        "detail.html",
        "form.html",
        "transfer_form.html",
        "transfers.html",
    )
] + [ROOT / "templates" / "partials" / "transaction_table.html"]


class TransactionTemplateTestCase(AuthenticatedTestCase):
    """Cria o minimo de dados para renderizar as telas de lancamentos."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.reserve = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("200.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")
        self.transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
            notes="Compra do mes",
        )

    def get_html(self, name, *args, **params):
        response = self.client.get(reverse(name, args=args), data=params)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()


class StackedListTests(TransactionTemplateTestCase):
    """Lista empilhada no celular e tabela no desktop (ADR-014, R-14)."""

    def test_list_uses_list_table_inside_a_card(self):
        html = self.get_html("transactions:list", year=2026, month=5)

        self.assertIn('class="list-table"', html)
        self.assertNotIn("data-table", html)
        self.assertNotIn("table-responsive", html)
        self.assertRegex(html, r'<section class="card[^"]*">\s*<table class="list-table"')

    def test_amount_cell_uses_list_table_amount_class(self):
        html = self.get_html("transactions:list", year=2026, month=5)

        self.assertRegex(html, r'<td class="list-table__amount[^"]*">\s*R\$ 250,00')

    def test_columns_stay_as_headers_for_the_desktop_table(self):
        html = self.get_html("transactions:list", year=2026, month=5)

        for column in ["Descrição", "Data", "Tipo", "Status", "Conta/Cartão", "Valor"]:
            self.assertIn(f">{column}</th>", html)

    def test_description_link_keeps_the_detail_querystring(self):
        html = self.get_html(
            "transactions:list", year=2026, month=5, status="", transaction_type=""
        )

        self.assertIn(
            reverse("transactions:detail", args=[self.transaction.id])
            + "?year=2026&amp;month=5&amp;status=&amp;transaction_type=",
            html,
        )

    def test_amount_is_colored_by_transaction_type(self):
        create_transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 9),
        )

        html = self.get_html("transactions:list", year=2026, month=5)

        self.assertRegex(html, r'tx-amount--income[^>]*>\s*R\$ 5\.000,00')
        self.assertRegex(html, r'tx-amount--expense[^>]*>\s*R\$ 250,00')

    def test_filters_use_the_collapsible_component(self):
        html = self.get_html("transactions:list", year=2026, month=5)

        self.assertIn('<details class="filters">', html)
        self.assertIn('name="status"', html)
        self.assertIn('name="transaction_type"', html)
        self.assertIn("Limpar filtros", html)

    def test_period_inputs_stay_outside_the_collapsible_filters(self):
        html = self.get_html("transactions:list", year=2026, month=5)

        details = html[html.index('<details class="filters">'):html.index("</details>")]
        self.assertNotIn('name="month"', details)
        self.assertNotIn('name="year"', details)
        self.assertIn('name="month"', html)
        self.assertIn('name="year"', html)

    def test_empty_state_uses_the_empty_component(self):
        html = self.get_html("transactions:list", year=2026, month=1)

        self.assertIn('class="empty"', html)
        self.assertIn("Nenhum lançamento encontrado", html)


class FilterSummaryTests(TransactionTemplateTestCase):
    """R-15: a contagem de filtros ativos aparece no resumo recolhido."""

    def summary(self, **params):
        html = self.get_html("transactions:list", year=2026, month=5, **params)
        return re.search(r'<summary class="filters__summary">(.*?)</summary>', html, re.S).group(1)

    def test_no_active_filter_shows_plain_label(self):
        self.assertEqual(self.summary(), "Filtros")

    def test_period_alone_does_not_count(self):
        self.assertEqual(self.summary(status="", transaction_type=""), "Filtros")

    def test_one_active_filter(self):
        self.assertEqual(self.summary(status="paid"), "Filtros (1 ativo)")
        self.assertEqual(self.summary(transaction_type="expense"), "Filtros (1 ativo)")

    def test_two_active_filters(self):
        self.assertEqual(
            self.summary(status="paid", transaction_type="expense"),
            "Filtros (2 ativos)",
        )


class ShellAndPageCssTests(TransactionTemplateTestCase):
    """Contrato da casca (ADR-019) e CSS da pagina (ADR-018)."""

    def urls(self):
        transfer = Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.account,
            destination_account=self.reserve,
            date=date(2026, 5, 8),
        )
        self.assertIsNotNone(transfer.id)
        return {
            "list": reverse("transactions:list"),
            "detail": reverse("transactions:detail", args=[self.transaction.id]),
            "transfers": reverse("transactions:transfers"),
            "create": reverse("transactions:create"),
            "edit": reverse("transactions:edit", args=[self.transaction.id]),
            "transfer-create": reverse("transactions:transfer-create"),
        }

    def body_class(self, url):
        html = self.client.get(url).content.decode()
        return re.search(r'<body class="([^"]+)"', html).group(1), html

    def test_every_screen_loads_the_page_css_after_the_shell_css(self):
        for name, url in self.urls().items():
            with self.subTest(screen=name):
                _, html = self.body_class(url)
                self.assertIn(PAGE_CSS, html)
                self.assertLess(html.index("css/layout.css"), html.index(PAGE_CSS))

    def test_form_screens_use_the_task_shell(self):
        urls = self.urls()
        for name in ("create", "edit", "transfer-create"):
            with self.subTest(screen=name):
                body, _ = self.body_class(urls[name])
                self.assertEqual(body, "shell-task")

    def test_browsing_screens_keep_the_navigation_shell(self):
        urls = self.urls()
        for name in ("list", "detail", "transfers"):
            with self.subTest(screen=name):
                body, _ = self.body_class(urls[name])
                self.assertEqual(body, "shell-nav")


class TransferListTests(TransactionTemplateTestCase):
    def test_transfers_use_list_table_with_origin_and_destination(self):
        Transfer.objects.create(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.account,
            destination_account=self.reserve,
            date=date(2026, 5, 8),
            notes="Reserva de maio",
        )

        html = self.get_html("transactions:transfers", year=2026, month=5)

        self.assertIn('class="list-table"', html)
        self.assertNotIn("data-table", html)
        for text in ["Aporte reserva", "Conta corrente", "Porquinho reserva", "R$ 300,00",
                     "08/05/2026", "Reserva de maio"]:
            self.assertIn(text, html)
        for column in ["Descrição", "Data", "Origem", "Destino", "Valor"]:
            self.assertIn(f">{column}</th>", html)

    def test_transfers_empty_state_uses_the_empty_component(self):
        html = self.get_html("transactions:transfers", year=2026, month=1)

        self.assertIn('class="empty"', html)
        self.assertIn("Nenhuma transferência encontrada.", html)


class DetailTemplateTests(TransactionTemplateTestCase):
    def test_detail_shows_the_same_data_in_summary_rows(self):
        html = self.get_html("transactions:detail", self.transaction.id)

        self.assertIn("summary-rows", html)
        for text in [
            "Mercado", "08/05/2026", "R$ 250,00", "Despesa", "Pago",
            "Conta corrente", "Alimentacao", "Não informado", "Não vinculada",
            "Compra do mes", "Observações", "Criado em", "Atualizado em",
        ]:
            self.assertIn(text, html)

    def test_detail_links_back_to_the_list_and_to_edit(self):
        html = self.get_html("transactions:detail", self.transaction.id)

        self.assertIn(f'href="{reverse("transactions:list")}"', html)
        self.assertIn(f'href="{reverse("transactions:edit", args=[self.transaction.id])}"', html)
        self.assertIn("Editar lançamento", html)

    def test_detail_hides_notes_block_without_notes(self):
        Transaction.objects.filter(pk=self.transaction.pk).update(notes="")

        html = self.get_html("transactions:detail", self.transaction.id)

        self.assertNotIn("Observações", html)


class FormTemplateTests(TransactionTemplateTestCase):
    def test_transaction_form_keeps_the_conditional_contract_of_app_js(self):
        html = self.get_html("transactions:create")

        self.assertIn('data-conditional-form="transaction"', html)
        self.assertIn('data-conditional-source="transaction-type"', html)
        self.assertIn('data-conditional-field="payment-source"', html)
        self.assertIn('<optgroup label="Contas">', html)
        # app.js procura o container em .form-field ou no pai direto do campo e o
        # rotulo no primeiro <span> do container: o campo precisa ser filho direto.
        self.assertRegex(
            html,
            r'<label class="field" for="id_source">\s*<span class="field__label">[^<]+</span>\s*<select name="source"',
        )

    def test_form_fields_use_the_field_component(self):
        html = self.get_html("transactions:create")

        self.assertIn('class="field"', html)
        self.assertIn("field__label", html)
        self.assertNotIn("form-field", html)
        self.assertNotIn("form-grid", html)

    def test_cancel_link_sits_at_the_top_and_primary_button_is_fixed_bar(self):
        html = self.get_html("transactions:create")

        main = html[html.index('id="content"'):]
        self.assertLess(main.index(reverse("transactions:list")), main.index("<form"))
        self.assertIn("Cancelar", main)
        self.assertRegex(main, r'<button class="btn btn--primary[^"]*" type="submit">Salvar</button>')

    def test_edit_form_cancel_goes_back_to_the_detail(self):
        html = self.get_html("transactions:edit", self.transaction.id)

        detail_url = reverse("transactions:detail", args=[self.transaction.id])
        self.assertLess(html.index(detail_url, html.index('id="content"')), html.index('<form class="tx-form"'))
        self.assertIn("Atualizar", html)

    def test_general_form_error_uses_alert_error(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        from transactions.forms import TransactionForm

        form = TransactionForm(data={})
        form.is_valid()
        form.add_error(None, "Erro geral do formulario.")
        request = RequestFactory().get("/transactions/create/")
        request.user = self.user

        html = render_to_string("transactions/form.html", {"form": form}, request=request)

        self.assertRegex(html, r'<div class="alert alert--error"[^>]*>[\s\S]*Erro geral do formulario\.')

    def test_field_error_uses_field_error_class(self):
        response = self.client.post(
            reverse("transactions:create"),
            data={"description": "", "amount": "100,00", "transaction_type": "expense"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="field__error"')

    def test_transfer_form_uses_task_screen_components(self):
        html = self.get_html("transactions:transfer-create")

        self.assertIn('class="field"', html)
        self.assertIn(reverse("transactions:transfers"), html)
        self.assertRegex(html, r'<button class="btn btn--primary[^"]*" type="submit">Salvar</button>')


class LegacyClassGuardTests(SimpleTestCase):
    """Os templates de lancamentos nao usam classe que so existia no antigo app.css."""

    def test_templates_do_not_use_legacy_only_classes(self):
        legacy_only = LEGACY_CLASS_NAMES - new_css_class_names()
        self.assertTrue((CSS_DIR / "pages" / "transactions.css").exists())

        for template in TEMPLATE_FILES:
            used = template_class_tokens(template.read_text(encoding="utf-8"))
            with self.subTest(template=template.name):
                self.assertEqual(sorted(used & legacy_only), [])

    def test_page_css_has_no_color_literal(self):
        css = (CSS_DIR / "pages" / "transactions.css").read_text(encoding="utf-8")

        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
