"""Tests dos importers do app imports."""

from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.test import SimpleTestCase

from imports.importers import (
    CsvTransactionImporter,
    OfxTransactionImporter,
    XlsxTransactionImporter,
    get_importer_for_source_type,
    normalize_description,
)
from imports.models import ImportedTransaction
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


class XlsxTransactionImporterTests(SimpleTestCase):
    """Garante o parsing inicial de arquivos XLSX."""

    def _xlsx_file(self, rows):
        """Monta um XLSX minimo em memoria para testes."""

        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for value in row:
                cells.append(f'<c t="inlineStr"><is><t>{value}</t></is></c>')
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
            "</worksheet>"
        )

        file_obj = BytesIO()
        with ZipFile(file_obj, "w", ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        file_obj.seek(0)
        return file_obj

    def test_parse_valid_xlsx_with_income_and_expense(self):
        """Deve ler XLSX simples preservando o tipo sugerido."""

        file_obj = self._xlsx_file(
            [
                ["date", "description", "amount", "external_id"],
                ["2026-05-10", "Mercado Dia", "-87.45", "FIT123"],
                ["2026-05-05", "Salario", "5000.00", ""],
            ]
        )

        rows = XlsxTransactionImporter().parse(file_obj)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].date, date(2026, 5, 10))
        self.assertEqual(rows[0].amount, Decimal("87.45"))
        self.assertEqual(rows[0].external_id, "FIT123")
        self.assertEqual(rows[0].suggested_transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(rows[1].suggested_transaction_type, Transaction.TransactionType.INCOME)

    def test_parse_xlsx_rejects_missing_required_columns(self):
        """Deve rejeitar XLSX sem colunas obrigatorias."""

        file_obj = self._xlsx_file([["date", "description"], ["2026-05-10", "Mercado"]])

        with self.assertRaisesMessage(ValueError, "XLSX sem colunas obrigatórias"):
            XlsxTransactionImporter().parse(file_obj)


class OfxTransactionImporterTests(SimpleTestCase):
    """Garante o parsing inicial de arquivos OFX."""

    def test_parse_valid_ofx_with_closed_tags(self):
        """Deve ler transacoes OFX com tags de fechamento."""

        file_obj = StringIO(
            """
            <OFX>
              <STMTTRN>
                <DTPOSTED>20260510120000[-3:BRT]</DTPOSTED>
                <TRNAMT>-87.45</TRNAMT>
                <FITID>OFX123</FITID>
                <MEMO>Mercado Dia</MEMO>
              </STMTTRN>
              <STMTTRN>
                <DTPOSTED>20260505</DTPOSTED>
                <TRNAMT>5000.00</TRNAMT>
                <FITID>OFX124</FITID>
                <NAME>Salario</NAME>
              </STMTTRN>
            </OFX>
            """
        )

        rows = OfxTransactionImporter().parse(file_obj)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].date, date(2026, 5, 10))
        self.assertEqual(rows[0].amount, Decimal("87.45"))
        self.assertEqual(rows[0].external_id, "OFX123")
        self.assertEqual(rows[0].suggested_transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(rows[1].suggested_transaction_type, Transaction.TransactionType.INCOME)

    def test_parse_valid_ofx_with_open_tags(self):
        """Deve ler transacoes OFX 1.x sem tags de fechamento."""

        file_obj = StringIO(
            """
            <OFX>
            <BANKTRANLIST>
            <STMTTRN>
            <DTPOSTED>20260510
            <TRNAMT>-87,45
            <FITID>OFX123
            <MEMO>Mercado Dia
            </BANKTRANLIST>
            </OFX>
            """
        )

        rows = OfxTransactionImporter().parse(file_obj)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].date, date(2026, 5, 10))
        self.assertEqual(rows[0].amount, Decimal("87.45"))
        self.assertEqual(rows[0].external_id, "OFX123")

    def test_parse_ofx_rejects_missing_amount(self):
        """Deve rejeitar transacao OFX sem valor."""

        file_obj = StringIO(
            """
            <OFX>
              <STMTTRN>
                <DTPOSTED>20260510</DTPOSTED>
                <MEMO>Mercado Dia</MEMO>
              </STMTTRN>
            </OFX>
            """
        )

        with self.assertRaisesMessage(ValueError, "OFX sem TRNAMT"):
            OfxTransactionImporter().parse(file_obj)


class ImporterFactoryTests(SimpleTestCase):
    """Garante a selecao de importers por tipo de fonte."""

    def test_get_importer_for_source_type_returns_supported_importers(self):
        """Deve retornar importer para CSV, XLSX e OFX."""

        self.assertIsInstance(
            get_importer_for_source_type(ImportedTransaction.SourceType.CSV),
            CsvTransactionImporter,
        )
        self.assertIsInstance(
            get_importer_for_source_type(ImportedTransaction.SourceType.XLSX),
            XlsxTransactionImporter,
        )
        self.assertIsInstance(
            get_importer_for_source_type(ImportedTransaction.SourceType.OFX),
            OfxTransactionImporter,
        )

    def test_get_importer_for_source_type_rejects_unknown_type(self):
        """Deve rejeitar tipos de importacao desconhecidos."""

        with self.assertRaisesMessage(ValueError, "Tipo de importacao nao suportado"):
            get_importer_for_source_type("pdf")
