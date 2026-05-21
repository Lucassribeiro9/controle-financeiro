"""Importers para o app imports."""

import csv
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.etree import ElementTree

from transactions.models import Transaction

from .models import ImportedTransaction


@dataclass(frozen=True)
class ImportedTransactionRow:
    """Representa uma linha de transacao normalizada de um arquivo externo."""

    date: date
    raw_description: str
    normalized_description: str
    amount: Decimal
    suggested_transaction_type: str
    external_id: str = ""


def normalize_description(description: str) -> str:
    """Remove espacos extras da descricao importada."""

    return " ".join(description.strip().split())


def _read_file_content(file_obj):
    """Le conteudo textual ou binario sem assumir o tipo do arquivo."""

    return file_obj.read()


def _decode_text(content) -> str:
    """Decodifica conteudo textual usando encodings comuns em extratos."""

    if isinstance(content, str):
        return content

    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("iso-8859-1")


def _parse_amount(raw_amount: str, *, line_number: int) -> Decimal:
    """Converte valor textual para Decimal."""

    try:
        amount = Decimal(raw_amount.strip().replace(",", "."))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError(f"Valor inválido na linha {line_number}: {raw_amount}") from exc

    if amount == Decimal("0.00"):
        raise ValueError(f"Valor zero não permitido na linha {line_number}")

    return amount


def _parse_iso_date(raw_date: str, *, line_number: int) -> date:
    """Converte data ISO para date."""

    try:
        return date.fromisoformat(raw_date.strip())
    except ValueError as exc:
        raise ValueError(f"Data inválida na linha {line_number}: {raw_date}") from exc


def _build_row(
    *,
    transaction_date: date,
    raw_description: str,
    raw_amount: Decimal,
    external_id: str = "",
) -> ImportedTransactionRow:
    """Monta uma linha importada normalizada a partir dos campos basicos."""

    normalized_description = normalize_description(raw_description)
    transaction_type = (
        Transaction.TransactionType.INCOME
        if raw_amount > Decimal("0.00")
        else Transaction.TransactionType.EXPENSE
    )

    return ImportedTransactionRow(
        date=transaction_date,
        raw_description=raw_description.strip(),
        normalized_description=normalized_description,
        amount=raw_amount.copy_abs(),
        suggested_transaction_type=transaction_type,
        external_id=external_id.strip(),
    )


class CsvTransactionImporter:
    """Importador de transacoes a partir de arquivos CSV."""

    required_fields = {"date", "description", "amount"}

    def parse(self, file_obj) -> list[ImportedTransactionRow]:
        """Parseia um CSV e retorna linhas normalizadas para staging."""

        content = _decode_text(_read_file_content(file_obj))
        reader = csv.DictReader(content.splitlines())
        missing_fields = self.required_fields - set(reader.fieldnames or [])

        if missing_fields:
            raise ValueError(
                f"CSV sem colunas obrigatórias: {', '.join(sorted(missing_fields))}"
            )

        rows = []

        for line_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue

            transaction_date = _parse_iso_date(row["date"], line_number=line_number)
            raw_amount = _parse_amount(row["amount"], line_number=line_number)

            rows.append(
                _build_row(
                    transaction_date=transaction_date,
                    raw_description=row["description"],
                    raw_amount=raw_amount,
                    external_id=row.get("external_id") or "",
                )
            )

        return rows


class XlsxTransactionImporter:
    """Importador de transacoes a partir de arquivos XLSX simples."""

    required_fields = {"date", "description", "amount"}

    def parse(self, file_obj) -> list[ImportedTransactionRow]:
        """Parseia a primeira planilha de um XLSX e retorna linhas normalizadas."""

        workbook = _read_file_content(file_obj)
        if isinstance(workbook, str):
            workbook = workbook.encode("utf-8")

        with zipfile.ZipFile(BytesIO(workbook)) as archive:
            shared_strings = self._read_shared_strings(archive)
            rows = self._read_first_sheet_rows(archive, shared_strings)

        if not rows:
            return []

        headers = [str(value).strip() for value in rows[0]]
        missing_fields = self.required_fields - set(headers)
        if missing_fields:
            raise ValueError(
                f"XLSX sem colunas obrigatórias: {', '.join(sorted(missing_fields))}"
            )

        column_indexes = {header: index for index, header in enumerate(headers)}
        imported_rows = []

        for line_number, row in enumerate(rows[1:], start=2):
            if not any(str(value).strip() for value in row):
                continue

            transaction_date = self._parse_xlsx_date(
                self._get_cell(row, column_indexes["date"]),
                line_number=line_number,
            )
            raw_amount = _parse_amount(
                self._get_cell(row, column_indexes["amount"]),
                line_number=line_number,
            )
            imported_rows.append(
                _build_row(
                    transaction_date=transaction_date,
                    raw_description=self._get_cell(row, column_indexes["description"]),
                    raw_amount=raw_amount,
                    external_id=self._get_cell(row, column_indexes.get("external_id")),
                )
            )

        return imported_rows

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        """Le a tabela de strings compartilhadas do XLSX, quando existir."""

        try:
            content = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []

        root = ElementTree.fromstring(content)
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        strings = []

        for item in root.findall("x:si", namespace):
            text_parts = [node.text or "" for node in item.findall(".//x:t", namespace)]
            strings.append("".join(text_parts))

        return strings

    def _read_first_sheet_rows(
        self,
        archive: zipfile.ZipFile,
        shared_strings: list[str],
    ) -> list[list[str]]:
        """Le as linhas da primeira planilha do arquivo."""

        content = archive.read("xl/worksheets/sheet1.xml")
        root = ElementTree.fromstring(content)
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows = []

        for row in root.findall(".//x:sheetData/x:row", namespace):
            values = []
            for cell in row.findall("x:c", namespace):
                values.append(self._read_cell_value(cell, shared_strings, namespace))
            rows.append(values)

        return rows

    def _read_cell_value(
        self,
        cell: ElementTree.Element,
        shared_strings: list[str],
        namespace: dict[str, str],
    ) -> str:
        """Extrai o valor textual de uma celula XLSX."""

        cell_type = cell.attrib.get("t")

        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell.findall(".//x:t", namespace))

        value = cell.find("x:v", namespace)
        if value is None or value.text is None:
            return ""

        if cell_type == "s":
            return shared_strings[int(value.text)]

        return value.text

    def _get_cell(self, row: list[str], index: int | None) -> str:
        """Busca uma celula por indice com fallback vazio."""

        if index is None or index >= len(row):
            return ""
        return str(row[index]).strip()

    def _parse_xlsx_date(self, raw_date: str, *, line_number: int) -> date:
        """Converte data ISO ou serial do Excel para date."""

        raw_date = raw_date.strip()
        try:
            return date.fromisoformat(raw_date)
        except ValueError:
            pass

        try:
            serial = int(Decimal(raw_date))
        except (ValueError, InvalidOperation) as exc:
            raise ValueError(f"Data inválida na linha {line_number}: {raw_date}") from exc

        return date(1899, 12, 30) + timedelta(days=serial)


class OfxTransactionImporter:
    """Importador de transacoes a partir de arquivos OFX."""

    def parse(self, file_obj) -> list[ImportedTransactionRow]:
        """Parseia transacoes STMTTRN de um arquivo OFX."""

        content = _decode_text(_read_file_content(file_obj))
        blocks = self._extract_transaction_blocks(content)
        rows = []

        for line_number, block in enumerate(blocks, start=1):
            raw_date = self._extract_tag(block, "DTPOSTED")
            raw_amount = self._extract_tag(block, "TRNAMT")
            raw_description = (
                self._extract_tag(block, "MEMO")
                or self._extract_tag(block, "NAME")
                or "Sem descricao"
            )
            external_id = self._extract_tag(block, "FITID")

            if not raw_date:
                raise ValueError(f"OFX sem DTPOSTED na transação {line_number}")
            if not raw_amount:
                raise ValueError(f"OFX sem TRNAMT na transação {line_number}")

            rows.append(
                _build_row(
                    transaction_date=self._parse_ofx_date(raw_date, line_number=line_number),
                    raw_description=raw_description,
                    raw_amount=_parse_amount(raw_amount, line_number=line_number),
                    external_id=external_id,
                )
            )

        return rows

    def _extract_transaction_blocks(self, content: str) -> list[str]:
        """Extrai blocos STMTTRN aceitando OFX com ou sem tag de fechamento."""

        closed_blocks = re.findall(
            r"<STMTTRN>(.*?)</STMTTRN>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if closed_blocks:
            return closed_blocks

        parts = re.split(r"<STMTTRN>", content, flags=re.IGNORECASE)[1:]
        blocks = []
        for part in parts:
            block = re.split(
                r"(?=<STMTTRN>|</BANKTRANLIST>|</CCSTMTRS>|</STMTRS>)",
                part,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            blocks.append(block)
        return blocks

    def _extract_tag(self, block: str, tag: str) -> str:
        """Extrai valor de tag OFX com suporte a tags fechadas e abertas."""

        closed_match = re.search(
            rf"<{tag}>(.*?)</{tag}>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if closed_match:
            return normalize_description(closed_match.group(1))

        open_match = re.search(
            rf"<{tag}>([^\r\n<]+)",
            block,
            flags=re.IGNORECASE,
        )
        if open_match:
            return normalize_description(open_match.group(1))

        return ""

    def _parse_ofx_date(self, raw_date: str, *, line_number: int) -> date:
        """Converte data OFX para date usando os oito primeiros digitos."""

        date_match = re.match(r"(\d{8})", raw_date.strip())
        if not date_match:
            raise ValueError(f"Data inválida na linha {line_number}: {raw_date}")

        return datetime.strptime(date_match.group(1), "%Y%m%d").date()


def get_importer_for_source_type(source_type):
    """Retorna o importer adequado para o formato solicitado."""

    importers = {
        ImportedTransaction.SourceType.CSV: CsvTransactionImporter,
        ImportedTransaction.SourceType.XLSX: XlsxTransactionImporter,
        ImportedTransaction.SourceType.OFX: OfxTransactionImporter,
    }

    try:
        return importers[source_type]()
    except KeyError as exc:
        raise ValueError(f"Tipo de importacao nao suportado: {source_type}") from exc
