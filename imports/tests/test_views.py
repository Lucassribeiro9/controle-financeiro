"""Tests das views do app imports."""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from categories.models import Category
from imports.models import ImportedTransaction
from institutions.models import Institution
from transactions.models import Transaction


class ImportViewTests(TestCase):
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

    def test_review_imports_lists_pending_items(self):
        """Deve listar importacoes pendentes para revisao."""

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
        self.assertEqual(response.json()["results"][0]["raw_description"], "Mercado Dia")

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
        self.assertEqual(response.url, reverse("imports:review-page"))
        self.assertEqual(transaction.description, "Mercado ajustado")
        self.assertEqual(transaction.amount, Decimal("90.50"))
        self.assertEqual(transaction.date, date(2026, 5, 11))
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)

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
