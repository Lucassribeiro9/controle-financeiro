"""Tests das views do app imports."""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from core.testing import AuthenticatedTestCase
from django.contrib.messages import get_messages
from django.urls import reverse

from accounts.models import FinancialAccount
from categories.models import Category
from imports.models import ImportedTransaction
from institutions.models import Institution
from transactions.models import Transaction


class ImportViewTests(AuthenticatedTestCase):
    """Garante os endpoints iniciais de importacao."""

    def setUp(self):
        """Cria dados base para confirmar importacoes."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")

    def _csv_file(self, content=None):
        """Monta um arquivo CSV em memoria para upload."""

        content = content or (
            "date,description,amount\n"
            "2026-05-10,Mercado Dia,-87.45\n"
            "2026-05-05,Salario,5000.00\n"
        )
        file_obj = BytesIO(content.encode("utf-8"))
        file_obj.name = "extrato.csv"
        return file_obj

    def _create_review_imports(self, *, total, status=ImportedTransaction.Status.PENDING):
        """Cria importacoes sequenciais para testes de listagem."""

        imported_transactions = []
        for day in range(1, total + 1):
            imported_transactions.append(
                ImportedTransaction.objects.create(
                    source_file_name="extrato.csv",
                    source_type=ImportedTransaction.SourceType.CSV,
                    raw_description=f"Lancamento {day:02d}",
                    normalized_description=f"Lancamento {day:02d}",
                    amount=Decimal("10.00"),
                    date=date(2026, 5, day),
                    status=status,
                )
            )
        return imported_transactions

    def test_upload_import_creates_pending_items(self):
        """Deve processar CSV e criar itens para revisao."""

        response = self.client.post(
            reverse("imports:upload"),
            {
                "source_type": ImportedTransaction.SourceType.CSV,
                "account_id": self.account.id,
                "file": self._csv_file(),
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(ImportedTransaction.objects.count(), 2)
        self.assertEqual(
            ImportedTransaction.objects.first().suggested_account,
            self.account,
        )

    def test_upload_import_page_renders_form(self):
        """Deve renderizar a pagina de upload de importacoes."""

        response = self.client.get(reverse("imports:upload-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "imports/upload.html")
        self.assertContains(response, "CSV")
        self.assertContains(response, "XLSX")
        self.assertContains(response, "OFX")
        self.assertContains(response, "Enviar para revisão")
        self.assertContains(response, self.account.name)

    def test_upload_import_page_post_redirects_to_review(self):
        """Deve processar upload pela tela e abrir revisao em HTML."""

        response = self.client.post(
            reverse("imports:upload-page"),
            {
                "source_type": ImportedTransaction.SourceType.CSV,
                "account_id": self.account.id,
                "file": self._csv_file(),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("imports:review-page"))
        self.assertEqual(ImportedTransaction.objects.count(), 2)

    def test_upload_import_requires_file(self):
        """Deve rejeitar upload sem arquivo."""

        response = self.client.post(reverse("imports:upload"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Campo file é obrigatório.")

    def test_upload_import_rejects_unsupported_source_type(self):
        """Deve rejeitar tipos nao suportados."""

        response = self.client.post(
            reverse("imports:upload"),
            {
                "source_type": "pdf",
                "file": self._csv_file(),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Tipo de importacao nao suportado", response.json()["error"])

    def test_upload_import_rejects_non_zip_xlsx(self):
        """Deve responder 400 quando o arquivo XLSX nao e um zip."""

        response = self.client.post(
            reverse("imports:upload"),
            {
                "source_type": ImportedTransaction.SourceType.XLSX,
                "file": self._csv_file(),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Arquivo XLSX inválido.")
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_upload_import_page_shows_message_for_non_zip_xlsx(self):
        """Deve mostrar a mensagem na tela de upload, sem erro 500."""

        response = self.client.post(
            reverse("imports:upload-page"),
            {
                "source_type": ImportedTransaction.SourceType.XLSX,
                "file": self._csv_file(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Arquivo XLSX inválido.")
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_upload_import_validation_error_cites_line_and_rolls_back(self):
        """Deve responder 400 citando a linha e desfazer o lote inteiro."""

        content = (
            "date,description,amount\n"
            "2026-10-01,Mercado,-10\n"
            "2026-10-02,Casa,-9999999999999\n"
        ).encode()
        upload = BytesIO(content)
        upload.name = "extrato.csv"

        response = self.client.post(
            reverse("imports:upload"),
            {"source_type": ImportedTransaction.SourceType.CSV, "file": upload},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Linha 3", response.json()["error"])
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_review_imports_lists_pending_items(self):
        """Deve listar importacoes para revisao."""

        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.PENDING,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Descartado",
            normalized_description="Descartado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 11),
            status=ImportedTransaction.Status.DISCARDED,
        )

        response = self.client.get(reverse("imports:review"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            {item["raw_description"] for item in response.json()["results"]},
            {"Mercado Dia"},
        )

        treated = self.client.get(reverse("imports:review"), data={"tab": "tratadas"})

        self.assertEqual(
            {item["raw_description"] for item in treated.json()["results"]},
            {"Descartado"},
        )

    def test_review_imports_filters_by_status_and_period(self):
        """Deve filtrar importacoes por status e periodo no endpoint JSON."""

        expected = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.PENDING,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Descartado",
            normalized_description="Descartado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 11),
            status=ImportedTransaction.Status.DISCARDED,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Antigo",
            normalized_description="Antigo",
            amount=Decimal("20.00"),
            date=date(2026, 4, 20),
            status=ImportedTransaction.Status.PENDING,
        )

        response = self.client.get(
            reverse("imports:review"),
            data={
                "status": ImportedTransaction.Status.PENDING,
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], expected.id)

    def test_review_imports_page_lists_pending_items(self):
        """Deve renderizar a pagina de revisao com importacoes pendentes."""

        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_category=self.category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.get(reverse("imports:review-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "imports/review.html")
        self.assertContains(response, "Mercado Dia")
        self.assertContains(response, "Confirmar")
        self.assertContains(response, "Pendente")
        self.assertContains(response, "Despesa")
        self.assertContains(response, "R$ 87,45")
        self.assertContains(response, 'class="status status--warning"', html=False)
        self.assertContains(response, 'class="filters"', html=False)
        self.assertContains(response, 'class="import-bulk"', html=False)
        self.assertContains(response, 'data-bulk-toggle="selected_imports"', html=False)
        self.assertContains(response, "Selecionar todos")
        self.assertContains(response, "Aplicar conta")
        self.assertContains(response, "Aplicar categoria")
        self.assertContains(response, "<details", html=False)

    def test_review_imports_page_filters_items(self):
        """Deve aplicar filtros na pagina de revisao."""

        ImportedTransaction.objects.create(
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )
        ImportedTransaction.objects.create(
            source_file_name="inter.ofx",
            source_type=ImportedTransaction.SourceType.OFX,
            raw_description="Padaria",
            normalized_description="Padaria",
            amount=Decimal("20.00"),
            date=date(2026, 5, 11),
            suggested_account=self.account,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.get(
            reverse("imports:review-page"),
            data={
                "source_file_name": "nubank.csv",
                "source_type": ImportedTransaction.SourceType.CSV,
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mercado Dia")
        self.assertNotContains(response, "Padaria")

    def test_review_imports_page_filters_by_status_and_period(self):
        """Deve aplicar e preservar filtros de status e periodo na tela, sem o select de status."""

        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.PENDING,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Descartado",
            normalized_description="Descartado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 11),
            status=ImportedTransaction.Status.DISCARDED,
        )
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Antigo",
            normalized_description="Antigo",
            amount=Decimal("20.00"),
            date=date(2026, 4, 20),
            status=ImportedTransaction.Status.PENDING,
        )

        response = self.client.get(
            reverse("imports:review-page"),
            data={
                "status": ImportedTransaction.Status.PENDING,
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mercado Dia")
        self.assertNotContains(response, "Descartado")
        self.assertNotContains(response, "Antigo")
        self.assertNotContains(response, '<select name="status">', html=False)
        self.assertContains(response, 'name="start_date"', html=False)
        self.assertContains(response, 'value="01/05/2026"', html=False)
        self.assertContains(response, 'value="31/05/2026"', html=False)
        self.assertNotContains(response, 'type="date"', html=False)

    def test_review_imports_page_paginates_review_items(self):
        """Deve paginar a revisao de importacoes."""

        self._create_review_imports(total=26)

        response = self.client.get(reverse("imports:review-page"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lancamento 26")
        self.assertContains(response, "Lancamento 02")
        self.assertNotContains(response, "Lancamento 01")
        self.assertContains(response, "Página 1 de 2")
        self.assertContains(response, "Próxima")
        self.assertContains(response, "?page=2", html=False)

    def test_review_imports_page_preserves_filters_in_pagination_links(self):
        """Deve preservar filtros ativos ao navegar entre paginas."""

        self._create_review_imports(total=26)
        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Descartado",
            normalized_description="Descartado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 27),
            status=ImportedTransaction.Status.DISCARDED,
        )

        response = self.client.get(
            reverse("imports:review-page"),
            data={
                "status": ImportedTransaction.Status.PENDING,
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
                "page": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lancamento 01")
        self.assertNotContains(response, "Descartado")
        self.assertContains(response, "Página 2 de 2")
        self.assertContains(response, "Anterior")
        self.assertContains(
            response,
            "?status=pending&amp;start_date=2026-05-01&amp;end_date=2026-05-31&amp;page=1",
            html=False,
        )

    def _import(self, name, status=ImportedTransaction.Status.PENDING, *, account=None,
                category=None, file_name="extrato.ofx", day=10):
        """Cria uma importacao para testes das abas."""

        return ImportedTransaction.objects.create(
            source_file_name=file_name,
            source_type=ImportedTransaction.SourceType.OFX,
            raw_description=name,
            normalized_description=name,
            amount=Decimal("10.00"),
            date=date(2026, 5, day),
            status=status,
            suggested_account=account,
            suggested_category=category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

    def _review_tab_fixture(self):
        Status = ImportedTransaction.Status
        self._import("Pronta", account=self.account, category=self.category)
        self._import("SemCategoria", account=self.account)
        self._import("SemConta", category=self.category)
        self._import("Duplicada", Status.DUPLICATE, account=self.account, category=self.category)
        self._import("Confirmada", Status.CONFIRMED, account=self.account)
        self._import("Descartada", Status.DISCARDED)

    def test_review_page_opens_on_pending_tab_with_counters(self):
        """A revisao abre em Pendentes e mostra os contadores das cinco abas."""

        self._review_tab_fixture()

        response = self.client.get(reverse("imports:review-page"))

        self.assertContains(response, "Pronta")
        self.assertContains(response, "Duplicada")
        self.assertNotContains(response, "Confirmada<")
        self.assertNotContains(response, "Descartada")
        self.assertEqual(response.context["active_tab"], "pendentes")
        self.assertEqual(
            [(tab["key"], tab["count"]) for tab in response.context["review_tabs"]],
            [
                ("pendentes", 4),
                ("sem-categoria", 1),
                ("sem-conta", 1),
                ("duplicadas", 1),
                ("tratadas", 2),
            ],
        )
        self.assertContains(response, 'aria-current="page"', html=False)

    def test_review_page_tab_param_selects_rows_and_invalid_falls_back(self):
        """O parametro tab escolhe a aba; valor invalido cai em Pendentes."""

        self._review_tab_fixture()

        treated = self.client.get(reverse("imports:review-page"), {"tab": "tratadas"})
        self.assertContains(treated, "Descartada")
        self.assertNotContains(treated, "SemConta")

        invalid = self.client.get(reverse("imports:review-page"), {"tab": "xpto"})
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.context["active_tab"], "pendentes")
        self.assertContains(invalid, "SemConta")

    def test_review_page_counters_respect_filters_and_tab_links_keep_them(self):
        """Contadores respeitam filtros e os links de aba mantem os filtros."""

        self._import("Em outro arquivo", file_name="outro.ofx")
        self._review_tab_fixture()

        response = self.client.get(
            reverse("imports:review-page"),
            {"source_file_name": "outro.ofx", "page": "3"},
        )

        counts = {tab["key"]: tab["count"] for tab in response.context["review_tabs"]}
        self.assertEqual(counts["pendentes"], 1)
        self.assertEqual(counts["tratadas"], 0)
        self.assertContains(
            response,
            "?source_file_name=outro.ofx&amp;tab=tratadas",
            html=False,
        )
        self.assertNotContains(response, "page=3&amp;tab")

    def test_review_page_empty_state_is_per_tab(self):
        """Cada aba vazia mostra a propria mensagem."""

        response = self.client.get(reverse("imports:review-page"))
        self.assertContains(response, "Nada pendente nesta importação")

        treated = self.client.get(reverse("imports:review-page"), {"tab": "tratadas"})
        self.assertNotContains(treated, "Nada pendente nesta importação")
        self.assertContains(treated, "Nenhuma importação tratada ainda")

    def test_review_page_treated_rows_have_no_actions(self):
        """Linhas tratadas nao mostram editar/descartar e a aba esconde o lote."""

        self._review_tab_fixture()

        treated = self.client.get(reverse("imports:review-page"), {"tab": "tratadas"})
        self.assertNotContains(treated, "import-row__edit")
        self.assertNotContains(treated, ">Descartar<", html=False)
        self.assertNotContains(treated, 'class="import-bulk"', html=False)

        pending = self.client.get(reverse("imports:review-page"))
        self.assertContains(pending, "import-row__edit")
        self.assertContains(pending, 'class="import-bulk"', html=False)

    def test_review_page_forms_carry_tab_filters_and_page(self):
        """Os formularios de acao devolvem a query completa da tela."""

        self._import("Pronta", account=self.account)

        response = self.client.get(
            reverse("imports:review-page"),
            {"tab": "sem-categoria", "source_file_name": "extrato.ofx", "page": "1"},
        )

        self.assertContains(
            response,
            'name="review_query" value="tab=sem-categoria&amp;source_file_name=extrato.ofx&amp;page=1"',
            html=False,
        )

    def test_review_page_get_does_not_write(self):
        """GET da revisao nao grava (ADR-012)."""

        self._review_tab_fixture()
        before = list(ImportedTransaction.objects.values_list("id", "status", "updated_at"))

        for tab in ("pendentes", "sem-categoria", "sem-conta", "duplicadas", "tratadas"):
            self.client.get(reverse("imports:review-page"), {"tab": tab})
            self.client.get(reverse("imports:review"), {"tab": tab})

        after = list(ImportedTransaction.objects.values_list("id", "status", "updated_at"))
        self.assertEqual(before, after)

    def test_confirm_from_page_redirect_keeps_tab_filters_and_page(self):
        """Confirmar pela tela volta para a mesma aba, filtros e pagina."""

        item = self._import("Pronta", account=self.account)
        query = "tab=sem-categoria&source_file_name=extrato.ofx&page=2"

        response = self.client.post(
            reverse("imports:confirm", kwargs={"imported_transaction_id": item.id}),
            {"next": "review-page", "review_query": query, "transaction_type": "expense"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('imports:review-page')}?{query}")

    def test_discard_from_page_redirect_keeps_tab_filters_and_page(self):
        """Descartar pela tela volta para a mesma aba, filtros e pagina."""

        item = self._import("Pronta", account=self.account)
        query = "tab=duplicadas&q=Pronta&page=2"

        response = self.client.post(
            reverse("imports:discard", kwargs={"imported_transaction_id": item.id}),
            {"next": "review-page", "review_query": query},
        )

        self.assertEqual(response.url, f"{reverse('imports:review-page')}?{query}")

    def test_bulk_review_redirect_keeps_tab_filters_and_page(self):
        """Acoes em lote voltam para a mesma aba, filtros e pagina."""

        item = self._import("Pronta", account=self.account)
        query = "tab=sem-categoria&q=Pronta&page=2"

        for payload in (
            {"bulk_action": "discard", "selected_imports": [item.id]},
            {"bulk_action": "confirm", "selected_imports": [item.id]},
            {"bulk_action": "apply_account"},
        ):
            response = self.client.post(
                reverse("imports:bulk-review"), {**payload, "review_query": query}
            )
            self.assertEqual(response.url, f"{reverse('imports:review-page')}?{query}")

    def test_confirmed_row_leaves_pending_tab_and_counters_update(self):
        """Depois de confirmar, a linha sai de Pendentes e entra em Tratadas."""

        item = self._import("Pronta", account=self.account, category=self.category)
        self.client.post(
            reverse("imports:confirm", kwargs={"imported_transaction_id": item.id}),
            {"next": "review-page", "transaction_type": "expense"},
        )

        pending = self.client.get(reverse("imports:review-page"))
        treated = self.client.get(reverse("imports:review-page"), {"tab": "tratadas"})

        self.assertNotContains(pending, "Pronta")
        self.assertContains(treated, "Pronta")
        counts = {tab["key"]: tab["count"] for tab in pending.context["review_tabs"]}
        self.assertEqual((counts["pendentes"], counts["tratadas"]), (0, 1))

    def test_confirm_import_creates_transaction(self):
        """Deve confirmar importacao e criar transacao real."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_category=self.category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse(
                "imports:confirm",
                kwargs={"imported_transaction_id": imported_transaction.id},
            )
        )

        imported_transaction.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.account.balance, Decimal("912.55"))

    def test_confirm_import_from_page_redirects_and_uses_edited_fields(self):
        """Deve confirmar pela tela usando os campos editaveis."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_category=self.category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse(
                "imports:confirm",
                kwargs={"imported_transaction_id": imported_transaction.id},
            ),
            {
                "next": "review-page",
                "review_query": "status=pending",
                "description": "Mercado ajustado",
                "date": "11/05/2026",
                "amount": "90,50",
                "account_id": self.account.id,
                "category_id": self.category.id,
                "transaction_type": Transaction.TransactionType.EXPENSE,
            },
        )

        transaction = Transaction.objects.get()
        imported_transaction.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('imports:review-page')}?status=pending")
        self.assertEqual(transaction.description, "Mercado ajustado")
        self.assertEqual(transaction.amount, Decimal("90.50"))
        self.assertEqual(transaction.date, date(2026, 5, 11))
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)

    def _pending_import(self, **overrides):
        """Cria uma importacao pendente pronta para confirmar."""

        data = dict(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )
        data.update(overrides)
        return ImportedTransaction.objects.create(**data)

    def _confirm(self, imported_transaction, data=None):
        return self.client.post(
            reverse("imports:confirm", kwargs={"imported_transaction_id": imported_transaction.id}),
            data or {},
        )

    def _upload_with_history_category(self):
        """Confirma uma linha com Lazer e importa outro arquivo com a mesma descricao."""

        leisure = Category.objects.create(name="Lazer")
        previous = self.client.post(
            reverse("imports:upload"),
            {
                "source_type": ImportedTransaction.SourceType.CSV,
                "account_id": self.account.id,
                "file": self._csv_file("date,description,amount\n2026-04-10,Cinema X,-30.00\n"),
            },
        )
        self.assertEqual(previous.status_code, 201)
        first = ImportedTransaction.objects.get()
        self.client.post(
            reverse("imports:confirm", kwargs={"imported_transaction_id": first.id}),
            {"account_id": self.account.id, "category_id": leisure.id},
        )
        self.client.post(
            reverse("imports:upload"),
            {
                "source_type": ImportedTransaction.SourceType.CSV,
                "account_id": self.account.id,
                "file": self._csv_file("date,description,amount\n2026-05-10,Cinema X,-35.00\n"),
            },
        )
        return leisure, ImportedTransaction.objects.get(
            status=ImportedTransaction.Status.PENDING
        )

    def test_history_category_is_editable_on_individual_confirm(self):
        """Deve permitir trocar a categoria sugerida pelo historico ao confirmar."""

        leisure, suggested = self._upload_with_history_category()
        self.assertEqual(suggested.suggested_category, leisure)

        response = self.client.post(
            reverse("imports:confirm", kwargs={"imported_transaction_id": suggested.id}),
            {"account_id": self.account.id, "category_id": self.category.id},
        )

        self.assertEqual(response.status_code, 200)
        suggested.refresh_from_db()
        self.assertEqual(suggested.confirmed_transaction.category, self.category)

    def test_history_category_is_editable_on_bulk_apply(self):
        """Deve permitir sobrescrever a categoria do historico no aplicar em lote."""

        leisure, suggested = self._upload_with_history_category()
        self.assertEqual(suggested.suggested_category, leisure)

        self.client.post(
            reverse("imports:bulk-review"),
            {
                "bulk_action": "apply_category",
                "bulk_category_id": self.category.id,
                "selected_imports": [suggested.id],
            },
        )

        suggested.refresh_from_db()
        self.assertEqual(suggested.suggested_category, self.category)

    def test_confirm_import_twice_creates_one_transaction(self):
        """Deve devolver 200 e manter um lancamento ao repetir o POST."""

        imported_transaction = self._pending_import()

        first = self._confirm(imported_transaction)
        second = self._confirm(imported_transaction)

        self.account.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.json()["confirmed_transaction_id"], second.json()["confirmed_transaction_id"]
        )
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.account.balance, Decimal("912.55"))

    def test_confirm_import_twice_from_page_shows_info_message(self):
        """Deve avisar que a importacao ja estava confirmada."""

        imported_transaction = self._pending_import()
        data = {"next": "review-page"}

        self._confirm(imported_transaction, data)
        response = self._confirm(imported_transaction, data)

        messages_text = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertEqual(response.status_code, 302)
        self.assertIn("Importação já confirmada.", messages_text)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_confirm_discarded_import_returns_400(self):
        """Deve recusar confirmar linha descartada."""

        imported_transaction = self._pending_import(status=ImportedTransaction.Status.DISCARDED)

        response = self._confirm(imported_transaction)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Só é possível confirmar importações pendentes ou duplicadas.",
        )
        self.assertEqual(Transaction.objects.count(), 0)

    def test_confirm_import_with_invalid_data_returns_400(self):
        """Deve responder 400, nao 500, quando o model recusa os dados."""

        imported_transaction = self._pending_import()

        response = self._confirm(imported_transaction, {"amount": "0"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        imported_transaction.refresh_from_db()
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.PENDING)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_confirm_import_with_invalid_data_from_page_shows_error(self):
        """Deve redirecionar com mensagem de erro na revisao."""

        imported_transaction = self._pending_import()

        response = self._confirm(imported_transaction, {"amount": "0", "next": "review-page"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(list(get_messages(response.wsgi_request))), 1)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_discard_confirmed_import_returns_400(self):
        """Deve recusar descartar linha confirmada."""

        imported_transaction = self._pending_import()
        self._confirm(imported_transaction)

        response = self.client.post(
            reverse("imports:discard", kwargs={"imported_transaction_id": imported_transaction.id})
        )

        imported_transaction.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Importação confirmada não pode ser descartada.")
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)
        self.assertIsNotNone(imported_transaction.confirmed_transaction)

    def test_confirm_import_requires_account(self):
        """Deve exigir conta quando nao houver sugestao salva."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse(
                "imports:confirm",
                kwargs={"imported_transaction_id": imported_transaction.id},
            )
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Informe account_id para confirmar.")

    def test_discard_import_marks_item_as_discarded(self):
        """Deve descartar importacao sem criar transacao."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse(
                "imports:discard",
                kwargs={"imported_transaction_id": imported_transaction.id},
            )
        )

        imported_transaction.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.DISCARDED)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_discard_import_from_page_redirects_to_review(self):
        """Deve descartar pela tela e voltar para a revisao."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse(
                "imports:discard",
                kwargs={"imported_transaction_id": imported_transaction.id},
            ),
            {"next": "review-page"},
        )

        imported_transaction.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("imports:review-page"))
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.DISCARDED)

    def test_bulk_review_discards_selected_imports(self):
        """Deve descartar importacoes selecionadas em lote."""

        first = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )
        second = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Padaria",
            normalized_description="Padaria",
            amount=Decimal("20.00"),
            date=date(2026, 5, 11),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse("imports:bulk-review"),
            {
                "bulk_action": "discard",
                "selected_imports": [first.id, second.id],
            },
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(first.status, ImportedTransaction.Status.DISCARDED)
        self.assertEqual(second.status, ImportedTransaction.Status.DISCARDED)

    def test_bulk_review_confirms_selected_imports_with_suggestions(self):
        """Deve confirmar em lote quando os itens possuem sugestoes minimas."""

        first = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_category=self.category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )
        second = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Salario",
            normalized_description="Salario",
            amount=Decimal("5000.00"),
            date=date(2026, 5, 5),
            suggested_account=self.account,
            suggested_transaction_type=Transaction.TransactionType.INCOME,
        )

        response = self.client.post(
            reverse("imports:bulk-review"),
            {
                "bulk_action": "confirm",
                "selected_imports": [first.id, second.id],
            },
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(first.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(second.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_bulk_review_applies_account_category_and_type(self):
        """Deve aplicar campos de revisao em lote pela tela HTML."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
        )

        account_response = self.client.post(
            reverse("imports:bulk-review"),
            {
                "bulk_action": "apply_account",
                "bulk_account_id": self.account.id,
                "selected_imports": [imported_transaction.id],
            },
        )
        category_response = self.client.post(
            reverse("imports:bulk-review"),
            {
                "bulk_action": "apply_category",
                "bulk_category_id": self.category.id,
                "selected_imports": [imported_transaction.id],
            },
        )
        imported_transaction.refresh_from_db()

        self.assertEqual(account_response.status_code, 302)
        self.assertEqual(category_response.status_code, 302)
        self.assertEqual(imported_transaction.suggested_account, self.account)
        self.assertEqual(imported_transaction.suggested_category, self.category)

    def test_bulk_review_confirms_partially_and_persists_row_error(self):
        """Deve confirmar validas e manter invalidas com erro ao confirmar em lote."""

        valid = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_category=self.category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )
        invalid = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Padaria",
            normalized_description="Padaria",
            amount=Decimal("20.00"),
            date=date(2026, 5, 11),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

        response = self.client.post(
            reverse("imports:bulk-review"),
            {
                "bulk_action": "confirm",
                "selected_imports": [valid.id, invalid.id],
            },
        )

        valid.refresh_from_db()
        invalid.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(valid.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(invalid.status, ImportedTransaction.Status.PENDING)
        self.assertEqual(invalid.review_error, "Informe uma conta para confirmar.")
        self.assertEqual(Transaction.objects.count(), 1)

    def test_confirm_import_validation_error_json_is_readable(self):
        imported_transaction = self._pending_import()
        error = ValidationError({"amount": ["Valor invalido."], "__all__": ["Erro geral."]})

        with patch("imports.views.confirm_imported_transaction", side_effect=error):
            response = self._confirm(imported_transaction)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Valor invalido. Erro geral."})

    def test_confirm_import_validation_error_message_is_readable(self):
        imported_transaction = self._pending_import()
        error = ValidationError({"amount": ["Valor invalido."]})

        with patch("imports.views.confirm_imported_transaction", side_effect=error):
            response = self.client.post(
                reverse(
                    "imports:confirm",
                    kwargs={"imported_transaction_id": imported_transaction.id},
                ),
                {"next": "review-page"},
                follow=True,
            )

        messages = [str(m) for m in response.context["messages"]]
        self.assertEqual(messages, ["Valor invalido."])


class OfxBankDetectionViewTests(AuthenticatedTestCase):
    """Garante a sugestao de conta pelo banco do OFX no upload."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
        )

    def _ofx(self, bank_block="<BANKID>0077</BANKID><ACCTID>123456789</ACCTID><ACCTTYPE>CHECKING</ACCTTYPE>"):
        header = f"<BANKACCTFROM>{bank_block}</BANKACCTFROM>" if bank_block else ""
        content = (
            f"<OFX>{header}<BANKTRANLIST><STMTTRN><DTPOSTED>20260510<TRNAMT>-10.00"
            "<FITID>A1<MEMO>Padaria</STMTTRN></BANKTRANLIST></OFX>"
        )
        file_obj = BytesIO(content.encode("utf-8"))
        file_obj.name = "extrato.ofx"
        return file_obj

    def _post(self, url_name, bank_block=None, **extra):
        data = {"source_type": ImportedTransaction.SourceType.OFX, "file": self._ofx(**(
            {"bank_block": bank_block} if bank_block is not None else {}))}
        data.update(extra)
        return self.client.post(reverse(url_name), data)

    def test_api_suggests_detected_account_and_reports_bank(self):
        response = self._post("imports:upload")

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["results"][0]["suggested_account_id"], self.account.id)
        self.assertEqual(body["bank_detection"]["institution"], "Inter")
        self.assertEqual(body["bank_detection"]["account"], "Conta corrente")
        self.assertEqual(body["bank_detection"]["masked_account_id"], "****6789")
        self.assertNotIn("123456789", response.content.decode())

    def test_page_shows_info_message_with_masked_account(self):
        response = self._post("imports:upload-page")

        self.assertEqual(response.status_code, 302)
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        info = [t for t in texts if "Inter" in t]
        self.assertEqual(len(info), 1)
        self.assertIn("****6789", info[0])
        self.assertIn("Conta corrente", info[0])
        self.assertNotIn("123456789", info[0])
        self.assertEqual(
            ImportedTransaction.objects.get().suggested_account, self.account
        )

    def test_chosen_account_prevails(self):
        other = FinancialAccount.objects.create(
            name="Poupanca", institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
        )

        response = self._post("imports:upload", account_id=other.id)

        self.assertEqual(response.json()["results"][0]["suggested_account_id"], other.id)

        page = self._post("imports:upload-page", account_id=other.id)
        texts = [str(m) for m in get_messages(page.wsgi_request)]
        self.assertTrue(any("Mantida a conta escolhida" in t for t in texts))

    def test_two_candidates_leave_rows_without_account(self):
        FinancialAccount.objects.create(
            name="Outra", institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
        )

        response = self._post("imports:upload")

        body = response.json()
        self.assertIsNone(body["results"][0]["suggested_account_id"])
        self.assertEqual(body["bank_detection"]["institution"], "Inter")
        self.assertIsNone(body["bank_detection"]["account"])

    def test_unknown_bank_behaves_as_before(self):
        response = self._post(
            "imports:upload", bank_block="<BANKID>999</BANKID><ACCTID>1</ACCTID>"
        )

        body = response.json()
        self.assertIsNone(body["bank_detection"])
        self.assertIsNone(body["results"][0]["suggested_account_id"])

    def test_ofx_without_bank_block_behaves_as_before(self):
        response = self._post("imports:upload", bank_block="")

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["bank_detection"])

    def test_page_without_detection_adds_no_bank_message(self):
        response = self._post("imports:upload-page", bank_block="")

        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertFalse(any("Banco identificado" in t for t in texts))

    def test_csv_upload_has_null_bank_detection(self):
        file_obj = BytesIO(b"date,description,amount\n2026-05-10,Mercado,-5.00\n")
        file_obj.name = "x.csv"

        response = self.client.post(
            reverse("imports:upload"),
            {"source_type": ImportedTransaction.SourceType.CSV, "file": file_obj},
        )

        self.assertIsNone(response.json()["bank_detection"])


class CsvProfileViewTests(AuthenticatedTestCase):
    """Garante o campo csv_profile no upload (spec 016, #268)."""

    FIXTURES = Path(__file__).parent / "fixtures" / "csv"

    def _upload_file(self, name="inter_extrato.csv", content=None):
        data = content if content is not None else (self.FIXTURES / name).read_bytes()
        file_obj = BytesIO(data)
        file_obj.name = name
        return file_obj

    def _post(self, url_name, profile=None, **extra):
        data = {"source_type": "csv", "file": self._upload_file(**extra.pop("file_kwargs", {}))}
        if profile is not None:
            data["csv_profile"] = profile
        data.update(extra)
        return self.client.post(reverse(url_name), data)

    def test_api_inter_profile_stages_rows_without_new_json_keys(self):
        response = self._post("imports:upload", "inter")

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["count"], 5)
        self.assertEqual(body["results"][0]["raw_description"], "Pix enviado - Mercado Exemplo")
        self.assertEqual(body["results"][0]["source_type"], "csv")
        self.assertEqual(set(body), {"bank_detection", "count", "results"})

    def test_api_nubank_profile_keeps_external_id(self):
        response = self._post(
            "imports:upload", "nubank", file_kwargs={"name": "nubank_extrato.csv"}
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["results"][0]["external_id"],
            "00000000-0000-4000-8000-000000000001",
        )

    def test_api_missing_column_returns_400_naming_it_without_writing(self):
        response = self._post(
            "imports:upload",
            "inter",
            file_kwargs={
                "content": "Data Lançamento;Descrição;Valor\n05/05/2026;Teste;-1,00\n".encode()
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Histórico", response.json()["error"])
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_api_unknown_profile_returns_400(self):
        response = self._post("imports:upload", "itau")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Perfil de CSV não suportado", response.json()["error"])
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_api_bank_profile_with_ofx_returns_400(self):
        response = self._post("imports:upload", "inter", source_type="ofx")

        self.assertEqual(response.status_code, 400)
        self.assertIn("só se aplica a CSV", response.json()["error"])
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_api_without_profile_behaves_as_generic(self):
        content = b"date,description,amount\n2026-05-10,Mercado Dia,-87.45\n"

        for profile in (None, "", "generic"):
            response = self._post(
                "imports:upload", profile, file_kwargs={"content": content}
            )
            self.assertEqual(response.status_code, 201)

        self.assertEqual(ImportedTransaction.objects.count(), 3)

    def test_api_generic_failure_hints_to_choose_the_bank(self):
        response = self._post("imports:upload", file_kwargs={"name": "inter_extrato.csv"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Banco do CSV", response.json()["error"])

    def test_page_post_with_profile_redirects_with_success(self):
        response = self._post("imports:upload-page", "inter")

        self.assertEqual(response.status_code, 302)
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("5 transação(ões) enviada(s)" in t for t in texts))
        self.assertEqual(ImportedTransaction.objects.count(), 5)

    def test_page_post_with_missing_column_shows_error_without_writing(self):
        response = self._post(
            "imports:upload-page",
            "nubank",
            file_kwargs={"name": "inter_extrato.csv"},
        )

        self.assertEqual(response.status_code, 200)
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("Identificador" in t for t in texts))
        self.assertEqual(ImportedTransaction.objects.count(), 0)

    def test_page_get_lists_profiles_and_does_not_write(self):
        response = self.client.get(reverse("imports:upload-page"))

        self.assertContains(response, 'name="csv_profile"')
        self.assertContains(response, 'value="nubank"')
        self.assertContains(response, 'value="inter"')
        self.assertEqual(ImportedTransaction.objects.count(), 0)


class ImportVisualMarkupTests(AuthenticatedTestCase):
    """Visual novo de upload e revisao (issue 295, spec 017)."""

    def setUp(self):
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=Institution.objects.create(name="Inter", code="077"),
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("100.00"),
        )

    def _create(self, description, *, status=ImportedTransaction.Status.PENDING, day=10):
        return ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description=description,
            normalized_description=description,
            amount=Decimal("10.00"),
            date=date(2026, 5, day),
            status=status,
            suggested_account=self.account,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )

    def _main_html(self, response):
        html = response.content.decode()
        return html[html.index("<main") : html.index("</main>")]

    def _legacy_classes_in(self, html):
        import re

        from core.tests.legacy_css import LEGACY_CLASS_NAMES, new_css_class_names

        legacy = LEGACY_CLASS_NAMES - new_css_class_names()
        used = set()
        for value in re.findall(r'class="([^"]*)"', html):
            used.update(value.split())
        return sorted(used & legacy)

    # Upload
    def test_upload_smoke_new_markup(self):
        response = self.client.get(reverse("imports:upload-page"))

        self.assertContains(response, "css/pages/imports.css")
        self.assertContains(response, "<h1>Importar extrato</h1>", html=True)
        self.assertContains(response, reverse("imports:review-page"))
        for name in ("source_type", "csv_profile", "file", "account_id"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, 'enctype="multipart/form-data"', html=False)
        self.assertContains(response, "btn btn--primary")

    def test_upload_has_no_legacy_classes(self):
        response = self.client.get(reverse("imports:upload-page"))

        self.assertEqual(self._legacy_classes_in(self._main_html(response)), [])

    # Revisao
    def test_review_smoke_new_markup(self):
        self._create("Mercado Dia")

        response = self.client.get(reverse("imports:review-page"))

        self.assertContains(response, "css/pages/imports.css")
        self.assertContains(response, "import-row")
        self.assertContains(response, 'data-bulk-toggle="selected_imports"', html=False)
        self.assertContains(response, "Filtros")
        self.assertIn("filter_form", response.context)
        self.assertEqual(response.context["active_filter_count"], 0)

    def test_review_has_no_legacy_classes(self):
        self._create("Mercado Dia")
        self._create("Duplicada", status=ImportedTransaction.Status.DUPLICATE)
        self._create("Tratada", status=ImportedTransaction.Status.DISCARDED)

        for params in ({}, {"tab": "tratadas"}, {"tab": "duplicadas"}, {"q": "zzz"}):
            response = self.client.get(reverse("imports:review-page"), params)
            self.assertEqual(self._legacy_classes_in(self._main_html(response)), [], params)

    def test_review_empty_state_uses_component(self):
        response = self.client.get(reverse("imports:review-page"))

        self.assertContains(response, 'class="empty"', html=False)
        self.assertContains(response, "Nada pendente nesta importação")

    def test_bulk_form_fields_unchanged(self):
        self._create("Mercado Dia")

        response = self.client.get(reverse("imports:review-page"))

        self.assertContains(response, f'action="{reverse("imports:bulk-review")}"', html=False)
        for token in (
            'name="bulk_account_id"',
            'name="bulk_category_id"',
            'name="review_query"',
            'name="bulk_action" value="apply_account"',
            'name="bulk_action" value="apply_category"',
            'name="bulk_action" value="confirm"',
            'name="bulk_action" value="discard"',
            'name="selected_imports"',
            'form="bulk-imports-form"',
        ):
            self.assertContains(response, token, html=False)
        self.assertContains(response, "<summary", html=False)
        self.assertContains(response, ">Ações<", html=False)

    def test_review_filters_dd_mm_aaaa(self):
        self._create("Dentro", day=10)
        self._create("Fora", day=25)

        response = self.client.get(
            reverse("imports:review-page"),
            {"start_date": "01/05/2026", "end_date": "15/05/2026"},
        )

        self.assertContains(response, "Dentro")
        self.assertNotContains(response, "Fora")
        self.assertEqual(response.context["active_filter_count"], 2)
        self.assertContains(response, "Filtros (2 ativos)")

    def test_review_filters_iso_still_work(self):
        self._create("Dentro", day=10)
        self._create("Fora", day=25)

        response = self.client.get(
            reverse("imports:review-page"),
            {"start_date": "2026-05-01", "end_date": "2026-05-15"},
        )

        self.assertContains(response, "Dentro")
        self.assertNotContains(response, "Fora")

    def test_review_invalid_date_is_200_with_field_error(self):
        self._create("Dentro", day=10)

        for value in ("31/02/2026", "2026-13-45", "abc"):
            response = self.client.get(reverse("imports:review-page"), {"start_date": value})

            self.assertEqual(response.status_code, 200, value)
            self.assertContains(response, "Dentro")
            self.assertIn("start_date", response.context["filter_form"].errors)

    def test_review_confirm_button_only_on_pending_cards(self):
        pending = self._create("Pendente")
        duplicate = self._create("Duplicada", status=ImportedTransaction.Status.DUPLICATE)

        response = self.client.get(reverse("imports:review-page"), {"q": ""})
        html = response.content.decode()
        pending_url = reverse("imports:confirm", args=[pending.id])
        duplicate_url = reverse("imports:confirm", args=[duplicate.id])

        # Atalho "Confirmar": form proprio, fora do <details> de edicao.
        shortcut = f'class="import-row__quick" method="post" action="{pending_url}"'
        self.assertIn(shortcut, html)
        self.assertNotIn(f'class="import-row__quick" method="post" action="{duplicate_url}"', html)
        quick = html[html.index(shortcut) :]
        quick = quick[: quick.index("</form>")]
        self.assertIn('name="next" value="review-page"', quick)
        self.assertIn('name="review_query"', quick)
        self.assertIn("btn btn--primary", quick)

        treated = self.client.get(reverse("imports:review-page"), {"tab": "tratadas"})
        self.assertNotContains(treated, "import-row__quick")

    def test_review_quick_confirm_posts_to_existing_endpoint(self):
        pending = self._create("Pendente")

        response = self.client.post(
            reverse("imports:confirm", args=[pending.id]),
            {"next": "review-page", "review_query": "tab=pendentes"},
        )

        self.assertEqual(response.status_code, 302)
        pending.refresh_from_db()
        self.assertEqual(pending.status, ImportedTransaction.Status.CONFIRMED)
