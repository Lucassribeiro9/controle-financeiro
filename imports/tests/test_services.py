"""Tests dos services do app imports."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from imports.importers import ImportedTransactionRow
from imports.models import ImportedTransaction
from imports.selectors import get_category_history
from imports.services import (
    apply_account_to_imports,
    apply_category_to_imports,
    build_import_hash,
    confirm_imported_transaction,
    confirm_imported_transactions_partially,
    detect_duplicate_import,
    discard_imported_transaction,
    stage_imported_transactions,
    suggest_category,
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

    def test_stage_validation_error_cites_line_and_rolls_back(self):
        """Deve virar ValueError com a linha de origem e desfazer o lote."""

        rows = [
            replace(self._row(), line_number=2),
            replace(self._row(amount=Decimal("9999999999999.00")), line_number=3),
        ]

        with self.assertRaisesMessage(ValueError, "Linha 3:"):
            stage_imported_transactions(
                file_name="extrato.csv",
                source_type=ImportedTransaction.SourceType.CSV,
                rows=rows,
            )

        self.assertEqual(ImportedTransaction.objects.count(), 0)

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

    def _stage(self, rows, **kwargs):
        return stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=rows,
            **kwargs,
        )

    def _statuses(self, imported):
        return [item.status for item in imported]

    def test_identical_rows_in_same_file_stay_pending(self):
        """Deve manter pendentes duas linhas iguais de um arquivo novo."""

        imported = self._stage([self._row(), self._row()])

        self.assertEqual(
            self._statuses(imported), [ImportedTransaction.Status.PENDING] * 2
        )

    def test_reimport_marks_same_number_of_occurrences_as_duplicate(self):
        """Deve marcar as duas ocorrencias ao reimportar o mesmo arquivo."""

        self._stage([self._row(), self._row()])

        imported = self._stage([self._row(), self._row()])

        self.assertEqual(
            self._statuses(imported), [ImportedTransaction.Status.DUPLICATE] * 2
        )

    def test_one_prior_import_marks_only_one_of_two_identical_rows(self):
        """Deve marcar so tantas duplicadas quantas importacoes anteriores existem."""

        self._stage([self._row()])

        imported = self._stage([self._row(), self._row()])

        self.assertEqual(
            self._statuses(imported),
            [ImportedTransaction.Status.DUPLICATE, ImportedTransaction.Status.PENDING],
        )

    def test_discarded_prior_import_still_counts(self):
        """Deve contar importacoes anteriores descartadas."""

        prior = self._stage([self._row()])[0]
        discard_imported_transaction(imported_transaction=prior)

        imported = self._stage([self._row()])

        self.assertEqual(imported[0].status, ImportedTransaction.Status.DUPLICATE)

    def test_same_external_id_twice_in_file_marks_second_as_duplicate(self):
        """Deve manter a regra por external_id dentro do mesmo arquivo."""

        imported = self._stage(
            [self._row(external_id="FIT1"), self._row(external_id="FIT1")]
        )

        self.assertEqual(
            self._statuses(imported),
            [ImportedTransaction.Status.PENDING, ImportedTransaction.Status.DUPLICATE],
        )

    def test_registered_transactions_mark_only_as_many_rows_as_exist(self):
        """Deve marcar no maximo K linhas quando ha K lancamentos iguais na conta."""

        Transaction.objects.create(
            description="Mercado Dia",
            amount=Decimal("87.45"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 10),
        )

        imported = self._stage([self._row(), self._row()], suggested_account=self.account)

        self.assertEqual(
            self._statuses(imported),
            [ImportedTransaction.Status.DUPLICATE, ImportedTransaction.Status.PENDING],
        )

    def test_suggest_category_matches_isolated_99_only(self):
        """Deve sugerir Transporte para o app 99 e nao para numeros que contem 99."""

        transport = Category.objects.create(name="Transporte")

        for description in ["99 POP", "99*CORRIDA", "CORRIDA 99"]:
            with self.subTest(description=description):
                self.assertEqual(suggest_category(description), transport)

        for description in ["LOJA 1999 LTDA", "PAG*AMAZON 99,90", "ITEM 99.90", "A99"]:
            with self.subTest(description=description):
                self.assertIsNone(suggest_category(description))

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

    def test_confirm_twice_with_stale_instance_creates_one_transaction(self):
        """Deve devolver o mesmo lancamento quando a instancia lida esta velha."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]
        stale = ImportedTransaction.objects.get(pk=imported_transaction.pk)

        first = confirm_imported_transaction(
            imported_transaction=imported_transaction, account=self.account
        )
        second = confirm_imported_transaction(imported_transaction=stale, account=self.account)

        self.account.refresh_from_db()
        self.assertEqual(first, second)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.account.balance, Decimal("912.55"))

    def test_confirm_discarded_import_is_rejected(self):
        """Deve recusar confirmacao de linha descartada."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]
        discard_imported_transaction(imported_transaction=imported_transaction)
        stale = ImportedTransaction.objects.get(pk=imported_transaction.pk)
        stale.status = ImportedTransaction.Status.PENDING

        with self.assertRaisesMessage(
            ValueError, "Só é possível confirmar importações pendentes ou duplicadas."
        ):
            confirm_imported_transaction(imported_transaction=stale, account=self.account)

        self.assertEqual(Transaction.objects.count(), 0)

    def test_confirm_duplicate_import_is_allowed(self):
        """Deve permitir confirmar linha marcada como duplicada."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]
        imported_transaction.status = ImportedTransaction.Status.DUPLICATE
        imported_transaction.save(update_fields=["status"])

        confirm_imported_transaction(imported_transaction=imported_transaction, account=self.account)

        imported_transaction.refresh_from_db()
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)

    def test_confirm_validation_error_keeps_status_and_creates_nothing(self):
        """Deve propagar ValidationError sem criar lancamento nem mudar o status."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]

        with self.assertRaises(ValidationError):
            confirm_imported_transaction(
                imported_transaction=imported_transaction,
                account=self.account,
                amount=Decimal("0.00"),
            )

        imported_transaction.refresh_from_db()
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.PENDING)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_discard_confirmed_import_is_rejected(self):
        """Deve recusar descarte de linha confirmada, mantendo o lancamento vinculado."""

        imported_transaction = stage_imported_transactions(
            file_name="extrato.csv",
            source_type=ImportedTransaction.SourceType.CSV,
            rows=[self._row()],
        )[0]
        transaction = confirm_imported_transaction(
            imported_transaction=imported_transaction, account=self.account
        )

        with self.assertRaisesMessage(
            ValueError, "Importação confirmada não pode ser descartada."
        ):
            discard_imported_transaction(imported_transaction=imported_transaction)

        imported_transaction.refresh_from_db()
        self.assertEqual(imported_transaction.status, ImportedTransaction.Status.CONFIRMED)
        self.assertEqual(imported_transaction.confirmed_transaction, transaction)

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


class CategoryHistoryStagingTests(TestCase):
    """Garante a sugestao de categoria pelo historico no staging (#267)."""

    def setUp(self):
        """Cria conta e categorias, com uma confirmacao previa de PADARIA X."""

        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.food = Category.objects.create(name="Alimentacao")
        self.transport = Category.objects.create(name="Transporte")
        self.leisure = Category.objects.create(name="Lazer")

    def _row(self, description, transaction_type=Transaction.TransactionType.EXPENSE, day=10):
        return ImportedTransactionRow(
            date=date(2026, 5, day),
            raw_description=description,
            normalized_description=description,
            amount=Decimal("12.00"),
            suggested_transaction_type=transaction_type,
            external_id="",
        )

    def _stage(self, rows, file_name="extrato.csv"):
        return stage_imported_transactions(
            file_name=file_name,
            source_type=ImportedTransaction.SourceType.CSV,
            rows=rows,
            suggested_account=self.account,
        )

    def _confirm(self, description, category):
        imported = self._stage([self._row(description, day=1)], file_name="anterior.csv")[0]
        confirm_imported_transaction(
            imported_transaction=imported, account=self.account, category=category
        )

    def test_history_category_is_suggested(self):
        """Deve sugerir a categoria usada na confirmacao anterior."""

        self._confirm("PADARIA X", self.leisure)

        imported = self._stage([self._row("PADARIA X", day=20)], file_name="novo.csv")

        self.assertEqual(imported[0].suggested_category, self.leisure)

    def test_history_wins_over_keyword(self):
        """Deve preferir o historico a palavra-chave."""

        self._confirm("UBER TRIP", self.leisure)

        imported = self._stage([self._row("UBER TRIP", day=20)], file_name="novo.csv")

        self.assertEqual(imported[0].suggested_category, self.leisure)

    def test_keyword_still_applies_without_history(self):
        """Deve manter a palavra-chave quando nao ha historico."""

        imported = self._stage([self._row("UBER TRIP")])

        self.assertEqual(imported[0].suggested_category, self.transport)

    def test_no_history_and_no_keyword_leaves_category_empty(self):
        """Deve deixar sem categoria quando nada casa."""

        imported = self._stage([self._row("LOJA QUALQUER")])

        self.assertIsNone(imported[0].suggested_category)

    def test_other_type_does_not_use_history(self):
        """Deve ignorar historico de outro tipo."""

        self._confirm("PADARIA X", self.leisure)

        imported = self._stage(
            [self._row("PADARIA X", Transaction.TransactionType.INCOME, day=20)],
            file_name="novo.csv",
        )

        self.assertIsNone(imported[0].suggested_category)

    def test_history_is_queried_once_per_file(self):
        """Deve consultar o historico uma vez por arquivo, nao por linha."""

        self._confirm("PADARIA X", self.leisure)
        rows = [self._row("PADARIA X", day=day) for day in (11, 12, 13, 14)]

        with patch(
            "imports.services.get_category_history", wraps=get_category_history
        ) as spy:
            self._stage(rows, file_name="novo.csv")

        self.assertEqual(spy.call_count, 1)

    def test_manual_transactions_are_not_history(self):
        """Deve ignorar lancamentos manuais com a mesma descricao."""

        Transaction.objects.create(
            description="PADARIA X",
            amount=Decimal("5.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.leisure,
            date=date(2026, 5, 2),
        )

        imported = self._stage([self._row("PADARIA X")])

        self.assertIsNone(imported[0].suggested_category)
