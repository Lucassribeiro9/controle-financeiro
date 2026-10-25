"""Tests das views do app imports."""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal
from io import BytesIO

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
        self.assertContains(response, "Enviar arquivo")
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
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            {item["raw_description"] for item in response.json()["results"]},
            {"Mercado Dia", "Descartado"},
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
        self.assertContains(response, 'class="badge badge-warning"', html=False)
        self.assertContains(response, 'class="filter-bar import-filter-bar"', html=False)
        self.assertContains(response, 'class="bulk-action-bar"', html=False)
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
        """Deve aplicar e preservar filtros de status e periodo na tela."""

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
        self.assertContains(
            response,
            f'<option value="{ImportedTransaction.Status.PENDING}" selected>',
            html=False,
        )
        self.assertContains(response, 'name="start_date" type="date" value="2026-05-01"', html=False)
        self.assertContains(response, 'name="end_date" type="date" value="2026-05-31"', html=False)

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
