"""Tests dos services do app imports."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from imports.importers import ImportedTransactionRow
from imports.models import ImportedTransaction
from imports.services import (
    apply_account_to_imports,
    apply_category_to_imports,
    build_import_hash,
    confirm_imported_transaction,
    confirm_imported_transactions_partially,
    detect_duplicate_import,
    discard_imported_transaction,
    stage_imported_transactions,
)
from institutions.models import Institution
from transactions.models import Transaction


class ImportServiceTests(TestCase):
    """Garante o fluxo de staging, confirmacao e descarte de importacoes."""

    def setUp(self):
        """Cria dados base para os cenarios de importacao."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")

    def _row(
        self,
        *,
        description="Mercado Dia",
        amount=Decimal("87.45"),
        transaction_type=Transaction.TransactionType.EXPENSE,
        external_id="",
    ):
        """Monta uma linha importada normalizada para os testes."""

        return ImportedTransactionRow(
            date=date(2026, 5, 10),
            raw_description=description,
            normalized_description=description,
            amount=amount,
            suggested_transaction_type=transaction_type,
            external_id=external_id,
        )

    def test_build_import_hash_is_stable(self):
        """Deve gerar o mesmo hash para os mesmos dados."""

        first_hash = build_import_hash(
            source_type=ImportedTransaction.SourceType.CSV,
            date=date(2026, 5, 10),
            amount=Decimal("87.45"),
            normalized_description="Mercado Dia",
        )
        second_hash = build_import_hash(
            source_type=ImportedTransaction.SourceType.CSV,
            date=date(2026, 5, 10),
            amount=Decimal("87.45"),
            normalized_description="Mercado Dia",
        )

        self.assertEqual(first_hash, second_hash)
        self.assertEqual(len(first_hash), 64)

    def test_stage_imported_transactions_creates_pending_items(self):
        """Deve salvar linhas importadas como pendencias de revisao."""

        imported = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
            suggested_account=self.account,
        )

        imported_transaction = imported[0]

        self.assertEqual(ImportedTransaction.objects.count(), 1)
        self.assertEqual(imported_transaction.source_file_name, "extrato.csv")
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.PENDING)
        self.assertEqual(imported_transaction.suggested_account, self.account)
        self.assertEqual(
            imported_transaction.suggested_transaction_type,
            Transaction.TransactionType.EXPENSE,
        )
        self.assertTrue(imported_transaction.import_hash)

    def test_stage_imported_transactions_marks_duplicate_by_hash(self):
        """Deve marcar duplicidade quando o hash da importacao ja existe."""

        row = self._row()
        stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[row],
        )

        imported = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[row],
        )

        self.assertEqual(imported[0].status, ImportedTransaction.Status.DUPLICATE)

    def test_stage_imported_transactions_marks_possible_duplicate_transaction(self):
        """Deve marcar duplicidade por data, valor, descricao normalizada e conta."""

        Transaction.objects.create(
            description="Mercado Dia",
            amount=Decimal("87.45"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 10),
        )

        imported = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row(description="  mercado   dia  ")],
            suggested_account=self.account,
        )

        self.assertEqual(imported[0].status, ImportedTransaction.Status.DUPLICATE)

    def test_detect_duplicate_import_uses_external_id(self):
        """Deve detectar duplicidade por identificador externo."""

        first = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row(external_id="FIT123")],
        )[0]
        candidate = ImportedTransaction(
            source_file_name="outro.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Outro",
            normalized_description="Outro",
            amount=Decimal("10.00"),
            date=date(2026, 5, 11),
            suggested_transaction_type=Transaction.TransactionType.EXPENSE,
            external_id=first.external_id,
        )

        self.assertTrue(detect_duplicate_import(imported_transaction=candidate))

    def test_confirm_imported_transaction_creates_transaction(self):
        """Deve confirmar importacao criando uma Transaction real."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
            suggested_account=self.account,
        )[0]

        transaction = confirm_imported_transaction(
            imported_transaction=imported_transaction,
            account=self.account,
            category=self.category,
        )

        imported_transaction.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(transaction.description, "Mercado Dia")
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(transaction.status, Transaction.PaymentStatus.PAID)
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(imported_transaction.confirmed_transaction, transaction)
        self.assertEqual(self.account.balance, Decimal("912.55"))

    def test_confirm_imported_transaction_requires_type(self):
        """Deve exigir tipo quando nao houver sugestao nem valor informado."""

        imported_transaction = ImportedTransaction.objects.create(
            source_file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            raw_description="Lancamento",
            normalized_description="Lancamento",
            amount=Decimal("10.00"),
            date=date(2026, 5, 10),
        )

        with self.assertRaisesMessage(ValueError, "Informe o tipo da transacao"):
            confirm_imported_transaction(
                imported_transaction=imported_transaction,
                account=self.account,
            )

    def test_discard_imported_transaction_marks_discarded(self):
        """Deve descartar importacao sem criar Transaction."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]

        discarded = discard_imported_transaction(imported_transaction=imported_transaction)

        self.assertEqual(discarded.status, ImportedTransaction.Status.DISCARDED)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_apply_account_to_imports_updates_selected_items(self):
        """Deve aplicar conta em lote somente aos itens selecionados."""

        first = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row(description="Mercado")],
        )[0]
        second = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row(description="Padaria")],
        )[0]

        result = apply_account_to_imports(
            selected_ids=[first.id],
            account=self.account,
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(result.processed, 1)
        self.assertEqual(first.suggested_account, self.account)
        self.assertIsNone(second.suggested_account)

    def test_apply_category_to_imports_updates_selected_items(self):
        """Deve aplicar categoria em lote aos itens selecionados."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]

        result = apply_category_to_imports(
            selected_ids=[imported_transaction.id],
            category=self.category,
        )

        imported_transaction.refresh_from_db()

        self.assertEqual(result.processed, 1)
        self.assertEqual(imported_transaction.suggested_category, self.category)

    def test_confirm_imported_transactions_partially_persists_row_errors(self):
        """Deve confirmar validas e manter invalidas com erro persistido."""

        valid = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row(description="Mercado")],
            suggested_account=self.account,
        )[0]
        invalid = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row(description="Padaria")],
        )[0]

        result = confirm_imported_transactions_partially(
            selected_ids=[valid.id, invalid.id],
        )

        valid.refresh_from_db()
        invalid.refresh_from_db()

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(valid.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(invalid.status, ImportedTransaction.Status.PENDING)
        self.assertEqual(invalid.review_error, "Informe uma conta para confirmar.")
        self.assertEqual(Transaction.objects.count(), 1)
