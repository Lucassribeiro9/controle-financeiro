"""Tests dos seletores do app imports."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from imports.models import ImportedTransaction
from imports.selectors import get_imported_transactions_for_review


class ImportSelectorTests(TestCase):
    """Garante as consultas de apoio para revisao de importacoes."""

    def test_get_imported_transactions_for_review_returns_all_statuses_by_default(self):
        """Deve listar todos os status por padrao."""

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
        discarded = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Descartado",
            normalized_description="Descartado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 11),
            status=ImportedTransaction.Status.DISCARDED,
        )

        imports = list(get_imported_transactions_for_review())

        self.assertEqual(imports, [discarded, duplicate, pending])

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

    def test_get_imported_transactions_for_review_filters_by_file_type_and_period(self):
        """Deve combinar filtros de arquivo, tipo e periodo."""

        expected = ImportedTransaction.objects.create(
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            status=ImportedTransaction.Status.PENDING,
        )
        ImportedTransaction.objects.create(
            source_file_name="inter.ofx",
            source_type=ImportedTransaction.SourceType.OFX,
            raw_description="Padaria",
            normalized_description="Padaria",
            amount=Decimal("20.00"),
            date=date(2026, 5, 11),
            status=ImportedTransaction.Status.PENDING,
        )
        ImportedTransaction.objects.create(
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Antigo",
            normalized_description="Antigo",
            amount=Decimal("10.00"),
            date=date(2026, 4, 20),
            status=ImportedTransaction.Status.PENDING,
        )

        imports = list(
            get_imported_transactions_for_review(
                source_file_name="nubank.csv",
                source_type=ImportedTransaction.SourceType.CSV,
                start_date="2026-05-01",
                end_date="2026-05-31",
            )
        )

        self.assertEqual(imports, [expected])
