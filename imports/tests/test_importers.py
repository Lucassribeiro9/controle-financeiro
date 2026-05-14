"""Tests dos importers do app imports."""

from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO

from django.test import SimpleTestCase

from imports.importers import CsvTransactionImporter, normalize_description
from transactions.models import Transaction


class CsvTransactionImporterTests(SimpleTestCase):
    """Garante o parsing inicial de arquivos CSV."""

    def test_parse_valid_csv_with_income_and_expense(self):
        """Deve ler receitas e despesas preservando o tipo sugerido."""

        file_obj = StringIO(
            "date,description,amount\n"
            "2026-05-10,Mercado Dia,-87.45\n"
            "2026-05-05,Salario,5000.00\n"
        )

        rows = CsvTransactionImporter().parse(file_obj)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].date, date(2026, 5, 10))
        self.assertEqual(rows[0].raw_description, "Mercado Dia")
        self.assertEqual(rows[0].amount, Decimal("87.45"))
        self.assertEqual(rows[0].suggested_transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(rows[1].amount, Decimal("5000.00"))
        self.assertEqual(rows[1].suggested_transaction_type, Transaction.TransactionType.INCOME)

    def test_parse_csv_with_external_id(self):
        """Deve capturar identificador externo quando a coluna existir."""

        file_obj = StringIO(
            "date,description,amount,external_id\n"
            "2026-05-10,Mercado Dia,-87.45,FIT123\n"
        )

        rows = CsvTransactionImporter().parse(file_obj)

        self.assertEqual(rows[0].external_id, "FIT123")

    def test_parse_ignores_empty_lines(self):
        """Deve ignorar linhas completamente vazias."""

        file_obj = StringIO(
            "date,description,amount\n"
            "\n"
            "2026-05-10,Mercado Dia,-87.45\n"
        )

        rows = CsvTransactionImporter().parse(file_obj)

        self.assertEqual(len(rows), 1)

    def test_parse_rejects_missing_required_columns(self):
        """Deve rejeitar CSV sem colunas obrigatorias."""

        file_obj = StringIO("date,description\n2026-05-10,Mercado Dia\n")

        with self.assertRaisesMessage(ValueError, "CSV sem colunas obrigatórias"):
            CsvTransactionImporter().parse(file_obj)

    def test_parse_rejects_invalid_date(self):
        """Deve rejeitar data fora do formato ISO."""

        file_obj = StringIO("date,description,amount\n10/05/2026,Mercado Dia,-87.45\n")

        with self.assertRaisesMessage(ValueError, "Data inválida na linha 2"):
            CsvTransactionImporter().parse(file_obj)

    def test_parse_rejects_invalid_amount(self):
        """Deve rejeitar valor monetario invalido."""

        file_obj = StringIO("date,description,amount\n2026-05-10,Mercado Dia,abc\n")

        with self.assertRaisesMessage(ValueError, "Valor inválido na linha 2"):
            CsvTransactionImporter().parse(file_obj)

    def test_parse_rejects_zero_amount(self):
        """Deve rejeitar lancamento com valor zerado."""

        file_obj = StringIO("date,description,amount\n2026-05-10,Mercado Dia,0.00\n")

        with self.assertRaisesMessage(ValueError, "Valor zero não permitido na linha 2"):
            CsvTransactionImporter().parse(file_obj)

    def test_parse_accepts_utf8_sig_bytes(self):
        """Deve ler arquivos enviados como bytes com BOM UTF-8."""

        file_obj = BytesIO(
            "date,description,amount\n2026-05-10,Mercado Dia,-87.45\n".encode(
                "utf-8-sig"
            )
        )

        rows = CsvTransactionImporter().parse(file_obj)

        self.assertEqual(rows[0].normalized_description, "Mercado Dia")

    def test_normalize_description_removes_extra_spaces(self):
        """Deve remover espacos extras da descricao."""

        self.assertEqual(normalize_description("  Mercado   Dia  "), "Mercado Dia")
