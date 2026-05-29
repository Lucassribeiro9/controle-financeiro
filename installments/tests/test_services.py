"""Tests dos servicos do app installments."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from categories.models import Category
from installments.models import InstallmentPlan
from installments.services import (
    cancel_installment_plan,
    create_installment_plan,
    get_installment_progress,
)
from institutions.models import Institution
from recurrences.models import Recurrence
from transactions.models import Transaction


class InstallmentPlanServiceTests(TestCase):
    """Garante regras de dominio para parcelamentos."""

    def setUp(self):
        """Cria dados base para os cenarios de parcelamento."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.payment_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )
        self.category = Category.objects.create(name="Eletronicos")

    def test_create_installment_plan_in_ten_installments(self):
        """Deve criar parcelamento de 10x."""

        plan = self._create_plan(total_amount=Decimal("1000.00"), installments=10)

        self.assertEqual(plan.total_installments, 10)
        self.assertEqual(plan.installment_amount, Decimal("100.00"))
        self.assertEqual(plan.status, InstallmentPlan.Status.ACTIVE)

    def test_create_installment_plan_generates_ten_transactions(self):
        """Deve gerar uma transacao por parcela."""

        plan = self._create_plan(total_amount=Decimal("1000.00"), installments=10)

        self.assertEqual(plan.transactions.count(), 10)
        self.assertEqual(
            plan.transactions.filter(
                transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            ).count(),
            10,
        )

    def test_installments_are_linked_to_correct_statements(self):
        """Cada parcela deve entrar na fatura correta."""

        plan = self._create_plan(
            total_amount=Decimal("1000.00"),
            installments=3,
            first_date=date(2026, 5, 8),
        )
        statements = list(
            plan.transactions.order_by("installment_number")
            .values_list("statement__month", "statement__year")
        )

        self.assertEqual(statements, [(5, 2026), (6, 2026), (7, 2026)])

    def test_installments_after_closing_day_follow_statement_rule(self):
        """Parcelas respeitam regra de fatura do cartao."""

        plan = self._create_plan(
            total_amount=Decimal("300.00"),
            installments=2,
            first_date=date(2026, 5, 21),
        )
        statements = list(
            plan.transactions.order_by("installment_number")
            .values_list("statement__month", "statement__year")
        )

        self.assertEqual(statements, [(6, 2026), (7, 2026)])

    def test_installments_sum_matches_total_amount(self):
        """A soma das parcelas deve fechar com o total."""

        plan = self._create_plan(total_amount=Decimal("999.99"), installments=10)

        total = sum(
            plan.transactions.values_list("amount", flat=True),
            Decimal("0.00"),
        )

        self.assertEqual(total, Decimal("999.99"))

    def test_last_installment_adjusts_cent_difference(self):
        """Ultima parcela deve ajustar diferenca de centavos."""

        plan = self._create_plan(total_amount=Decimal("100.00"), installments=3)
        amounts = list(
            plan.transactions.order_by("installment_number").values_list(
                "amount",
                flat=True,
            )
        )

        self.assertEqual(amounts, [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")])

    def test_installment_purchase_does_not_create_recurrence(self):
        """Compra parcelada nao deve virar recorrencia."""

        self._create_plan(total_amount=Decimal("1000.00"), installments=10)

        self.assertEqual(Recurrence.objects.count(), 0)

    def test_cancel_installment_plan_cancels_pending_transactions(self):
        """Cancelamento deve marcar parcelas pendentes como canceladas."""

        plan = self._create_plan(total_amount=Decimal("1000.00"), installments=10)
        
        # Simula uma parcela ja paga
        first_transaction = plan.transactions.first()
        first_transaction.status = Transaction.PaymentStatus.PAID
        first_transaction.save()

        canceled_plan = cancel_installment_plan(plan=plan)

        self.assertEqual(canceled_plan.status, InstallmentPlan.Status.CANCELED)
        
        # A primeira continua paga
        first_transaction.refresh_from_db()
        self.assertEqual(first_transaction.status, Transaction.PaymentStatus.PAID)
        
        # As outras 9 devem estar canceladas
        self.assertEqual(
            plan.transactions.filter(status=Transaction.PaymentStatus.CANCELED).count(),
            9,
        )

    def test_cancel_completed_plan_raises_validation_error(self):
        """Nao deve cancelar parcelamento concluido."""

        plan = self._create_plan(total_amount=Decimal("1000.00"), installments=10)
        plan.status = InstallmentPlan.Status.COMPLETED
        plan.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ValidationError):
            cancel_installment_plan(plan=plan)

    def test_get_installment_progress_returns_generated_amount(self):
        """Deve retornar progresso do parcelamento."""

        plan = self._create_plan(total_amount=Decimal("100.00"), installments=3)

        progress = get_installment_progress(plan=plan)

        self.assertEqual(progress["generated_count"], 3)
        self.assertEqual(progress["generated_amount"], Decimal("100.00"))

    def _create_plan(
        self,
        *,
        total_amount,
        installments,
        first_date=date(2026, 5, 8),
    ):
        """Cria plano de parcelamento para testes."""

        return create_installment_plan(
            description="Notebook",
            total_amount=total_amount,
            total_installments=installments,
            first_installment_date=first_date,
            card=self.card,
            category=self.category,
        )
