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
        """Deve rejeitar data que nao seja ISO nem dd/mm/aaaa."""

        file_obj = StringIO("date,description,amount\n31/02/2026,Mercado Dia,-87.45\n")

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
        """Deve rejeitar data que nao seja ISO nem dd/mm/aaaa."""

        file_obj = StringIO("date,description,amount\n31/02/2026,Mercado Dia,-87.45\n")

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

    def _xlsx_file_from_sheet_xml(self, sheet_xml):
        """Monta um XLSX minimo a partir do XML da primeira planilha."""

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

    def test_parse_xlsx_preserves_empty_cells_by_reference(self):
        """Deve preservar colunas quando uma celula vazia e omitida no XML."""

        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1">'
            '<c r="A1" t="inlineStr"><is><t>date</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>description</t></is></c>'
            '<c r="C1" t="inlineStr"><is><t>amount</t></is></c>'
            '<c r="D1" t="inlineStr"><is><t>external_id</t></is></c>'
            "</row>"
            '<row r="2">'
            '<c r="A2" t="inlineStr"><is><t>2026-05-10</t></is></c>'
            '<c r="C2" t="inlineStr"><is><t>-87.45</t></is></c>'
            '<c r="D2" t="inlineStr"><is><t>FIT123</t></is></c>'
            "</row>"
            "</sheetData>"
            "</worksheet>"
        )

        rows = XlsxTransactionImporter().parse(
            self._xlsx_file_from_sheet_xml(sheet_xml)
        )

        self.assertEqual(rows[0].raw_description, "")
        self.assertEqual(rows[0].amount, Decimal("87.45"))
        self.assertEqual(rows[0].external_id, "FIT123")


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


class CsvBrazilianFormatTests(SimpleTestCase):
    """Garante o formato brasileiro de extratos CSV (spec 014, #234)."""

    def _parse(self, text):
        return CsvTransactionImporter().parse(StringIO(text))

    def test_unquoted_decimal_comma_is_rejected_for_extra_columns(self):
        """Deve recusar valor com virgula sem aspas, que o CSV parte em duas colunas."""

        with self.assertRaisesMessage(
            ValueError, "Linha 2 tem mais colunas que o cabeçalho."
        ):
            self._parse("date,description,amount\n2026-10-01,Mercado,-10,50\n")

    def test_unquoted_thousands_and_decimal_comma_is_rejected(self):
        """Deve recusar `-1.234,56` sem aspas em vez de importar R$ 1,234."""

        with self.assertRaisesMessage(
            ValueError, "Linha 2 tem mais colunas que o cabeçalho."
        ):
            self._parse("date,description,amount\n2026-10-01,Mercado,-1.234,56\n")

    def test_quoted_brazilian_amount_is_read(self):
        """Deve ler `"-1.234,56"` entre aspas como despesa de R$ 1.234,56."""

        rows = self._parse('date,description,amount\n2026-10-01,Mercado,"-1.234,56"\n')

        self.assertEqual(rows[0].amount, Decimal("1234.56"))
        self.assertEqual(
            rows[0].suggested_transaction_type, Transaction.TransactionType.EXPENSE
        )

    def test_brazilian_date_is_accepted(self):
        """Deve aceitar data dd/mm/aaaa."""

        rows = self._parse("date,description,amount\n01/10/2026,Mercado,-10\n")

        self.assertEqual(rows[0].date, date(2026, 10, 1))

    def test_semicolon_delimiter_with_portuguese_headers(self):
        """Deve ler extrato `Data;Descrição;Valor` com valores BR."""

        rows = self._parse(
            "Data;Descrição;Valor\n"
            "01/10/2026;Mercado;-1.234,56\n"
            "02/10/2026;Salario;5.000,00\n"
        )

        self.assertEqual([row.amount for row in rows], [Decimal("1234.56"), Decimal("5000.00")])
        self.assertEqual(rows[0].date, date(2026, 10, 1))
        self.assertEqual(rows[0].raw_description, "Mercado")

    def test_header_aliases_ignore_case_and_accents(self):
        """Deve aceitar HISTÓRICO e Identificador sem diferenciar caixa e acento."""

        rows = self._parse(
            "DATA,HISTÓRICO,VALOR,Identificador\n2026-10-01,Mercado,-10.50,FIT1\n"
        )

        self.assertEqual(rows[0].raw_description, "Mercado")
        self.assertEqual(rows[0].amount, Decimal("10.50"))
        self.assertEqual(rows[0].external_id, "FIT1")

    def test_repeated_header_field_is_rejected(self):
        """Deve recusar duas colunas que mapeiam para o mesmo campo."""

        with self.assertRaisesMessage(
            ValueError, "Cabeçalho com coluna repetida: description"
        ):
            self._parse("date,description,historico,amount\n2026-10-01,A,B,-1\n")

    def test_short_row_is_rejected(self):
        """Deve recusar linha com menos colunas que o cabecalho."""

        with self.assertRaisesMessage(
            ValueError, "Linha 2 tem menos colunas que o cabeçalho."
        ):
            self._parse("date,description,amount\n2026-10-01,Mercado\n")

    def test_amount_formats(self):
        """Deve ler virgula como decimal e ponto sem virgula como decimal."""

        cases = {
            "-10,50": Decimal("10.50"),
            "1.234.567,89": Decimal("1234567.89"),
            "1234.56": Decimal("1234.56"),
            "-87.45": Decimal("87.45"),
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                rows = self._parse(f'date,description,amount\n2026-10-01,A,"{raw}"\n')
                self.assertEqual(rows[0].amount, expected)

    def test_amount_with_more_than_two_decimals_is_rejected(self):
        """Deve recusar valor ambiguo ou com casas extras, sem arredondar."""

        for raw in ["1.234", "10,505", "1,234.56", "NaN", "Infinity"]:
            with self.subTest(raw=raw):
                with self.assertRaisesMessage(ValueError, "Valor inválido na linha 2"):
                    self._parse(f'date,description,amount\n2026-10-01,A,"{raw}"\n')

    def test_two_digit_year_is_rejected(self):
        """Deve recusar dd/mm/aa."""

        with self.assertRaisesMessage(ValueError, "Data inválida na linha 2"):
            self._parse("date,description,amount\n01/10/26,A,-1\n")


class XlsxBrazilianFormatTests(SimpleTestCase):
    """Garante o mesmo parse BR de valor, data e cabecalho no XLSX."""

    _xlsx_file = XlsxTransactionImporterTests._xlsx_file

    def test_brazilian_values_dates_and_headers(self):
        """Deve ler Data/Descrição/Valor com valor e data em formato BR."""

        file_obj = self._xlsx_file(
            [
                ["Data", "Descrição", "Valor"],
                ["01/10/2026", "Mercado", "-1.234,56"],
            ]
        )

        rows = XlsxTransactionImporter().parse(file_obj)

        self.assertEqual(rows[0].date, date(2026, 10, 1))
        self.assertEqual(rows[0].amount, Decimal("1234.56"))

    def test_xlsx_serial_date_still_works(self):
        """Deve manter o serial do Excel como data valida."""

        file_obj = self._xlsx_file(
            [["date", "description", "amount"], ["46296", "Mercado", "-10"]]
        )

        rows = XlsxTransactionImporter().parse(file_obj)

        self.assertEqual(rows[0].date, date(2026, 10, 1))

    def test_xlsx_repeated_header_field_is_rejected(self):
        """Deve recusar duas colunas que mapeiam para o mesmo campo."""

        file_obj = self._xlsx_file(
            [["date", "description", "descricao", "amount"], ["2026-10-01", "A", "B", "-1"]]
        )

        with self.assertRaisesMessage(
            ValueError, "Cabeçalho com coluna repetida: description"
        ):
            XlsxTransactionImporter().parse(file_obj)
