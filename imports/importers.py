"""Importers para o app imports."""

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from transactions.models import Transaction


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


class CsvTransactionImporter:
    """Importador de transações a partir de arquivos CSV."""

    required_fields = {"date", "description", "amount"}

    def parse(self, file_obj) -> list[ImportedTransactionRow]:
        """Parseia um CSV e retorna linhas normalizadas para staging."""

        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")

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

            try:
                transaction_date = date.fromisoformat(row["date"].strip())
            except ValueError as exc:
                raise ValueError(
                    f"Data inválida na linha {line_number}: {row['date']}"
                ) from exc

            try:
                raw_amount = Decimal(row["amount"].strip())
            except (ValueError, InvalidOperation) as exc:
                raise ValueError(
                    f"Valor inválido na linha {line_number}: {row['amount']}"
                ) from exc

            if raw_amount == Decimal("0.00"):
                raise ValueError(f"Valor zero não permitido na linha {line_number}")

            raw_description = row["description"].strip()
            normalized_description = normalize_description(raw_description)
            transaction_type = (
                Transaction.TransactionType.INCOME
                if raw_amount > Decimal("0.00")
                else Transaction.TransactionType.EXPENSE
            )

            rows.append(
                ImportedTransactionRow(
                    date=transaction_date,
                    raw_description=raw_description,
                    normalized_description=normalized_description,
                    amount=raw_amount.copy_abs(),
                    suggested_transaction_type=transaction_type,
                    external_id=(row.get("external_id") or "").strip(),
                )
            )
        return rows
