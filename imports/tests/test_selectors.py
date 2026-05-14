"""Tests dos seletores do app imports."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from imports.models import ImportedTransaction
from imports.selectors import get_imported_transactions_for_review


class ImportSelectorTests(TestCase):
    """Garante as consultas de apoio para revisao de importacoes."""

    def test_get_imported_transactions_for_review_returns_pending_and_duplicates(self):
        """Deve listar apenas importacoes que precisam de revisao por padrao."""

        pending = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.PENDING,
        )
        duplicate = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.DUPLICATE,
            import_hash="abc",
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

        imports = list(get_imported_transactions_for_review())

        self.assertEqual(imports, [duplicate, pending])

    def test_get_imported_transactions_for_review_filters_by_status(self):
        """Deve permitir filtro explicito por status."""

        ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.PENDING,
        )
        discarded = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Descartado",
            normalized_description="Descartado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 11),
            status=ImportedTransaction.Status.DISCARDED,
        )

        imports = list(
            get_imported_transactions_for_review(
                status=ImportedTransaction.Status.DISCARDED
            )
        )

        self.assertEqual(imports, [discarded])
