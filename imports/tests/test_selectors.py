"""Tests dos seletores do app imports."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from imports.models import ImportedTransaction
from imports.selectors import IMPORT_REVIEW_PAGE_SIZE
from imports.selectors import get_imported_transactions_for_review
from imports.selectors import paginate_imported_transactions_for_review
from institutions.models import Institution
from transactions.models import Transaction


class ImportSelectorTests(TestCase):
    """Garante as consultas de apoio para revisao de importacoes."""

    def setUp(self):
        """Cria dados base para filtros por relacionamento."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")

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

    def test_get_imported_transactions_for_review_filters_by_status_and_period(self):
        """Deve combinar status e periodo na revisao."""

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
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Confirmado",
            normalized_description="Confirmado",
            amount=Decimal("10.00"),
            date=date(2026, 5, 12),
            status=ImportedTransaction.Status.CONFIRMED,
            confirmed_transaction=None,
        )
        ImportedTransaction.objects.create(
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Antigo",
            normalized_description="Antigo",
            amount=Decimal("20.00"),
            date=date(2026, 4, 20),
            status=ImportedTransaction.Status.PENDING,
        )

        imports = list(
            get_imported_transactions_for_review(
                status=ImportedTransaction.Status.PENDING,
                start_date="2026-05-01",
                end_date="2026-05-31",
            )
        )

        self.assertEqual(imports, [expected])

    def test_get_imported_transactions_for_review_filters_by_account_category_type_and_text(self):
        """Deve filtrar por conta, categoria, tipo sugerido e texto."""

        expected = ImportedTransaction.objects.create(
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Mercado Dia",
            normalized_description="Mercado Dia",
            amount=Decimal("87.45"),
            date=date(2026, 5, 10),
            suggested_account=self.account,
            suggested_category=self.category,
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
        )
        ImportedTransaction.objects.create(
            source_file_name="nubank.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Salario",
            normalized_description="Salario",
            amount=Decimal("5000.00"),
            date=date(2026, 5, 5),
            suggested_account=self.account,
            suggested_transaction_type=Transaction.TransactionType.INCOME,
        )

        imports = list(
            get_imported_transactions_for_review(
                account_id=self.account.id,
                category_id=self.category.id,
                transaction_type=Transaction.TransactionType.EXPENSE,
                q="mercado",
            )
        )

        self.assertEqual(imports, [expected])

    def test_paginate_imported_transactions_for_review_splits_review_items(self):
        """Deve paginar itens de revisao usando tamanho padrao."""

        oldest = None
        for day in range(1, IMPORT_REVIEW_PAGE_SIZE + 2):
            imported_transaction = ImportedTransaction.objects.create(
                source_file_name="extrato.csv",
                source_type=ImportedTransaction.SourceType.CSV,
                raw_description=f"Lancamento {day:02d}",
                normalized_description=f"Lancamento {day:02d}",
                amount=Decimal("10.00"),
                date=date(2026, 5, day),
                status=ImportedTransaction.Status.PENDING,
            )
            if day == 1:
                oldest = imported_transaction

        queryset = get_imported_transactions_for_review(
            status=ImportedTransaction.Status.PENDING
        )

        first_page = paginate_imported_transactions_for_review(
            queryset=queryset,
            page_number=1,
        )
        second_page = paginate_imported_transactions_for_review(
            queryset=queryset,
            page_number=2,
        )

        self.assertEqual(first_page.paginator.per_page, IMPORT_REVIEW_PAGE_SIZE)
        self.assertEqual(len(first_page.object_list), IMPORT_REVIEW_PAGE_SIZE)
        self.assertEqual(len(second_page.object_list), 1)
        self.assertEqual(second_page.object_list[0], oldest)
