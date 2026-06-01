"""Tests dos serviços do app transactions."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from cards.models import CardStatement
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction
from transactions.services import (
    create_transaction,
    create_transaction_by_payment_method,
    create_transfer,
    mark_transaction_as_paid,
    update_transaction,
)


class TransactionServiceTests(TestCase):
    """Garante as regras de negocio para criacao de transacoes."""

    def setUp(self):
        """Cria dados base para os cenarios de transacao."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )
        self.benefit_card = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("300.00"),
            balance=Decimal("300.00"),
        )

    def test_create_pending_income_does_not_change_account_balance(self):
        """Receita pendente nao deve alterar saldo da conta."""

        transaction = create_transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertIsNotNone(transaction.id)
        self.assertEqual(transaction.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_create_paid_income_increases_account_balance(self):
        """Receita paga deve aumentar saldo da conta."""

        transaction = create_transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertIsNotNone(transaction.id)
        self.assertEqual(self.account.balance, Decimal("6000.00"))

    def test_create_pending_expense_does_not_change_account_balance(self):
        """Despesa pendente nao deve alterar saldo da conta."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertIsNotNone(transaction.id)
        self.assertEqual(transaction.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_create_paid_expense_decreases_account_balance(self):
        """Despesa paga deve reduzir o saldo da conta."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertIsNotNone(transaction.id)
        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_create_paid_statement_payment_decreases_account_balance(self):
        """Pagamento de fatura pago deve reduzir saldo da conta."""

        create_transaction(
            description="Pagamento fatura",
            amount=Decimal("400.00"),
            transaction_type=Transaction.TransactionType.STATEMENT_PAYMENT,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("600.00"))

    def test_create_forecast_does_not_change_account_balance(self):
        """Nao deve alterar saldo ao criar uma previsao."""

        create_transaction(
            description="Internet prevista",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_create_card_purchase_does_not_change_payment_account_balance(self):
        """Nao deve alterar saldo da conta ao criar compra no cartao."""

        create_transaction(
            description="Compra no cartao",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.card,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("1000.00"))

    def test_create_transaction_by_payment_method_creates_debit_transaction(self):
        """Debito deve usar o service orquestrador sem alterar o dominio interno."""

        transaction = create_transaction_by_payment_method(
            payment_method="debit",
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.account.refresh_from_db()

        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_create_transaction_by_payment_method_creates_credit_purchase_with_statement(self):
        """Credito deve criar compra vinculada a fatura do mesmo cartao."""

        transaction = create_transaction_by_payment_method(
            payment_method="credit",
            description="Compra online",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.CARD_PURCHASE)
        self.assertEqual(transaction.card, self.card)
        self.assertIsInstance(transaction.statement, CardStatement)
        self.assertEqual(transaction.statement.card, self.card)

    def test_create_transaction_by_payment_method_creates_inline_installment_plan(self):
        """Credito com parcelas deve criar parcelamento inline no mesmo fluxo."""

        plan = create_transaction_by_payment_method(
            payment_method="credit",
            description="Notebook",
            amount=Decimal("1000.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            total_installments=10,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.assertEqual(plan.total_installments, 10)
        self.assertEqual(plan.total_amount, Decimal("1000.00"))
        self.assertEqual(plan.transactions.count(), 10)
        first_installment = plan.transactions.order_by("installment_number").first()
        self.assertEqual(first_installment.card, self.card)
        self.assertEqual(first_installment.installment_plan, plan)
        self.assertEqual(first_installment.installment_number, 1)

    def test_create_transaction_by_payment_method_debits_benefit_balance(self):
        """Beneficio deve consumir o saldo proprio do cartao."""

        transaction = create_transaction_by_payment_method(
            payment_method="benefit",
            description="Almoco",
            amount=Decimal("35.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.benefit_card,
            category=self.category,
            date=date(2026, 5, 8),
        )

        self.benefit_card.refresh_from_db()

        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.CARD_PURCHASE)
        self.assertEqual(transaction.card, self.benefit_card)
        self.assertEqual(self.benefit_card.balance, Decimal("265.00"))
        self.assertIsNone(transaction.statement)

    def test_create_benefit_purchase_rolls_back_balance_when_transaction_fails(self):
        """Falha apos debito nao deve persistir reducao de saldo."""

        with patch(
            "transactions.services.Transaction.save",
            side_effect=RuntimeError("falha ao salvar transacao"),
        ):
            with self.assertRaisesMessage(RuntimeError, "falha ao salvar transacao"):
                create_transaction_by_payment_method(
                    payment_method="benefit",
                    description="Almoco",
                    amount=Decimal("35.00"),
                    transaction_type=Transaction.TransactionType.CARD_PURCHASE,
                    status=Transaction.PaymentStatus.PENDING,
                    card=self.benefit_card,
                    category=self.category,
                    date=date(2026, 5, 8),
                )

        self.benefit_card.refresh_from_db()

        self.assertEqual(self.benefit_card.balance, Decimal("300.00"))
        self.assertFalse(Transaction.objects.filter(description="Almoco").exists())

    def test_create_transaction_by_payment_method_rejects_insufficient_benefit_balance(self):
        """Beneficio deve bloquear compra maior que saldo disponivel."""

        with self.assertRaisesMessage(
            ValidationError,
            "Saldo insuficiente no cartão de benefício.",
        ):
            create_transaction_by_payment_method(
                payment_method="benefit",
                description="Compra alta",
                amount=Decimal("350.00"),
                transaction_type=Transaction.TransactionType.CARD_PURCHASE,
                status=Transaction.PaymentStatus.PENDING,
                card=self.benefit_card,
                category=self.category,
                date=date(2026, 5, 8),
            )

        self.benefit_card.refresh_from_db()

        self.assertEqual(self.benefit_card.balance, Decimal("300.00"))
        self.assertFalse(Transaction.objects.filter(description="Compra alta").exists())

    def test_create_transaction_by_payment_method_rejects_transfer(self):
        """Transferencia nao deve entrar pelo orquestrador de lancamento."""

        with self.assertRaisesMessage(
            ValidationError,
            "Transferência deve ser criada pelo fluxo de transferências.",
        ):
            create_transaction_by_payment_method(
                payment_method="transfer",
                description="Aporte reserva",
                amount=Decimal("100.00"),
                transaction_type=Transaction.TransactionType.ADJUSTMENT,
                date=date(2026, 5, 8),
            )

    def test_mark_transaction_as_paid_updates_status(self):
        """Deve marcar uma transacao como paga."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        paid_transaction = mark_transaction_as_paid(transaction.id)

        self.assertEqual(paid_transaction.status, Transaction.PaymentStatus.PAID)

    def test_mark_pending_expense_as_paid_decreases_account_balance(self):
        """Marcar despesa pendente como paga deve reduzir saldo."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )
        self.account.refresh_from_db()
        balance_after_creation = self.account.balance

        mark_transaction_as_paid(transaction.id)

        self.account.refresh_from_db()

        self.assertEqual(balance_after_creation, Decimal("1000.00"))
        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_mark_paid_transaction_as_paid_does_not_apply_balance_twice(self):
        """Nao deve alterar saldo novamente ao marcar transacao ja paga."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )
        self.account.refresh_from_db()
        balance_after_creation = self.account.balance

        mark_transaction_as_paid(transaction.id)

        self.account.refresh_from_db()

        self.assertEqual(balance_after_creation, Decimal("750.00"))
        self.assertEqual(self.account.balance, balance_after_creation)

    def test_mark_paid_transaction_as_paid_is_idempotent(self):
        """Nao deve alterar saldo ao marcar como paga uma transacao ja paga."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        mark_transaction_as_paid(transaction.id)
        mark_transaction_as_paid(transaction.id)

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_mark_pending_income_as_paid_increases_account_balance(self):
        """Marcar receita pendente como paga deve aumentar saldo."""

        transaction = create_transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        mark_transaction_as_paid(transaction.id)

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("6000.00"))

    def test_update_pending_transaction_allows_changes(self):
        """Lançamento pendente deve poder ser atualizado."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        updated = update_transaction(
            transaction_id=transaction.id,
            description="Mercado maior",
            amount=Decimal("300.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            status=Transaction.PaymentStatus.PENDING,
            date=date(2026, 5, 9),
            notes="Atualizado",
        )

        self.assertEqual(updated.description, "Mercado maior")
        self.assertEqual(updated.amount, Decimal("300.00"))
        self.assertEqual(updated.date, date(2026, 5, 9))

    def test_update_pending_transaction_can_mark_as_paid(self):
        """Lançamento pendente pode ser editado para pago e impactar saldo."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        updated = update_transaction(
            transaction_id=transaction.id,
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            status=Transaction.PaymentStatus.PAID,
            date=date(2026, 5, 8),
            notes="",
        )

        self.account.refresh_from_db()

        self.assertEqual(updated.status, Transaction.PaymentStatus.PAID)
        self.assertEqual(self.account.balance, Decimal("750.00"))

    def test_update_paid_expense_adjusts_previous_balance_impact(self):
        """Editar despesa paga deve reverter impacto anterior e aplicar novo."""

        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        update_transaction(
            transaction_id=transaction.id,
            description="Mercado editado",
            amount=Decimal("300.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            category=self.category,
            status=Transaction.PaymentStatus.PAID,
            date=date(2026, 5, 9),
            notes="",
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("700.00"))

    def test_update_paid_income_adjusts_previous_balance_impact(self):
        """Editar receita paga deve reverter impacto anterior e aplicar novo."""

        transaction = create_transaction(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        update_transaction(
            transaction_id=transaction.id,
            description="Salario ajustado",
            amount=Decimal("4500.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account,
            category=self.category,
            status=Transaction.PaymentStatus.PAID,
            date=date(2026, 5, 8),
            notes="",
        )

        self.account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("5500.00"))

    def test_update_paid_transaction_moves_balance_between_accounts(self):
        """Trocar conta de lancamento pago deve desfazer antiga e aplicar nova."""

        destination_account = FinancialAccount.objects.create(
            name="Conta reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        transaction = create_transaction(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 8),
        )

        update_transaction(
            transaction_id=transaction.id,
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=destination_account,
            category=self.category,
            status=Transaction.PaymentStatus.PAID,
            date=date(2026, 5, 8),
            notes="",
        )

        self.account.refresh_from_db()
        destination_account.refresh_from_db()

        self.assertEqual(self.account.balance, Decimal("1000.00"))
        self.assertEqual(destination_account.balance, Decimal("250.00"))

    def test_update_credit_purchase_recalculates_statement_when_date_changes(self):
        """Alterar data de compra no credito deve mover e recalcular faturas."""

        transaction = create_transaction_by_payment_method(
            payment_method="credit",
            description="Compra online",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            category=self.category,
            date=date(2026, 5, 8),
        )
        old_statement = transaction.statement

        update_transaction(
            transaction_id=transaction.id,
            description="Compra online",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.card,
            category=self.category,
            status=Transaction.PaymentStatus.PENDING,
            date=date(2026, 5, 21),
            notes="",
        )

        transaction.refresh_from_db()
        old_statement.refresh_from_db()
        new_statement = transaction.statement

        self.assertNotEqual(new_statement, old_statement)
        self.assertEqual(old_statement.expected_amount, Decimal("0.00"))
        self.assertEqual(new_statement.expected_amount, Decimal("200.00"))

    def test_update_benefit_purchase_adjusts_card_balance(self):
        """Editar compra em beneficio deve refazer consumo do saldo proprio."""

        transaction = create_transaction_by_payment_method(
            payment_method="benefit",
            description="Almoco",
            amount=Decimal("35.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.benefit_card,
            category=self.category,
            date=date(2026, 5, 8),
        )

        update_transaction(
            transaction_id=transaction.id,
            description="Almoco",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.benefit_card,
            category=self.category,
            status=Transaction.PaymentStatus.PENDING,
            date=date(2026, 5, 8),
            notes="",
        )

        self.benefit_card.refresh_from_db()

        self.assertEqual(self.benefit_card.balance, Decimal("250.00"))

    def test_update_credit_purchase_rejects_paid_statement_change(self):
        """Compra vinculada a fatura paga nao deve ser alterada."""

        transaction = create_transaction_by_payment_method(
            payment_method="credit",
            description="Compra online",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=self.card,
            category=self.category,
            date=date(2026, 5, 8),
        )
        statement = transaction.statement
        statement.status = CardStatement.StatementStatus.PAID
        statement.save(update_fields=["status", "updated_at"])

        with self.assertRaisesMessage(
            ValidationError,
            "Fatura paga nao permite alteracao de compras.",
        ):
            update_transaction(
                transaction_id=transaction.id,
                description="Compra online",
                amount=Decimal("200.00"),
                transaction_type=Transaction.TransactionType.CARD_PURCHASE,
                card=self.card,
                category=self.category,
                status=Transaction.PaymentStatus.PENDING,
                date=date(2026, 5, 8),
                notes="",
            )


class TransferServiceTests(TestCase):
    """Garante as regras de negócio para criação de transferências."""

    def setUp(self):
        """Cria contas base para os cenarios de transferencia."""

        self.institution = Institution.objects.create(name="Inter", code="077")

        self.source_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

        self.destination_account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("200.00"),
        )

    def test_create_valid_transfer(self):
        """Deve criar transferencia valida usando o servico."""

        transfer = create_transfer(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        self.assertIsNotNone(transfer.id)
        self.assertEqual(transfer.amount, Decimal("300.00"))
        self.assertEqual(transfer.from_account, self.source_account)
        self.assertEqual(transfer.destination_account, self.destination_account)

    def test_create_transfer_moves_balance_between_accounts(self):
        """Deve reduzir origem e aumentar destino ao criar transferencia."""

        create_transfer(
            description="Aporte reserva",
            amount=Decimal("300.00"),
            from_account=self.source_account,
            destination_account=self.destination_account,
            date=date(2026, 5, 8),
        )

        self.source_account.refresh_from_db()
        self.destination_account.refresh_from_db()

        self.assertEqual(self.source_account.balance, Decimal("700.00"))
        self.assertEqual(self.destination_account.balance, Decimal("500.00"))
