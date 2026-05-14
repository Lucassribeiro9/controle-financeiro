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

    def test_upload_import_requires_file(self):
        """Deve rejeitar upload sem arquivo."""

        response = self.client.post(reverse("imports:upload"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Campo file e obrigatorio.")

    def test_upload_import_rejects_unsupported_source_type(self):
        """Deve rejeitar tipos desconhecidos."""

        response = self.client.post(
            reverse("imports:upload"),
            {
                "source_type": "pdf",
                "file": self._csv_file(),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Tipo de importacao nao suportado", response.json()["error"])

    def test_upload_import_accepts_ofx(self):
        """Deve processar OFX e criar itens para revisao."""

        file_obj = BytesIO(
            b"""
            <OFX>
              <STMTTRN>
                <DTPOSTED>20260510</DTPOSTED>
                <TRNAMT>-87.45</TRNAMT>
                <FITID>OFX123</FITID>
                <MEMO>Mercado Dia</MEMO>
              </STMTTRN>
            </OFX>
            """
        )
        file_obj.name = "extrato.ofx"

        response = self.client.post(
            reverse("imports:upload"),
            {
                "source_type": ImportedTransaction.SourceType.OFX,
                "account_id": self.account.id,
                "file": file_obj,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(ImportedTransaction.objects.first().source_type, "ofx")

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
