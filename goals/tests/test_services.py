"""Tests dos servicos do app goals."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from goals.services import (
    calculate_goal_progress,
    create_monthly_goal_from_goal,
    create_reduction_goal_for_category,
    calculate_monthly_goal_status,
    refresh_monthly_goals,
    update_monthly_goal_status,
    validate_goal_accounts_currency,
)
from institutions.models import Institution
from transactions.models import Transaction


class GoalServiceTests(TestCase):
    """Garante as regras de negocio para objetivos e metas mensais."""

    def setUp(self):
        """Cria dados base para cenarios de objetivos."""

        patcher = mock.patch(
            "goals.services.timezone.localdate", return_value=date(2026, 5, 20)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1500.00"),
        )
        self.extra_account = FinancialAccount.objects.create(
            name="Poupanca",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        self.spending_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Delivery")

    def test_calculate_accumulation_goal_progress_uses_linked_accounts_balance(self):
        """Deve calcular progresso de acumulo somando contas vinculadas."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("10000.00"),
            start_date=date(2026, 5, 1),
        )
        goal.accounts.add(self.account, self.extra_account)

        progress = calculate_goal_progress(goal=goal)

        self.assertEqual(progress["current_amount"], Decimal("2000.00"))
        self.assertEqual(progress["target_amount"], Decimal("10000.00"))
        self.assertEqual(progress["remaining_amount"], Decimal("8000.00"))
        self.assertEqual(progress["progress_percent"], Decimal("20.00"))

    def test_calculate_reduction_goal_progress_uses_category_expenses_for_month(self):
        """Deve calcular progresso de reducao com despesas da categoria no mes."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Pizza",
            amount=Decimal("80.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        Transaction.objects.create(
            description="Lanche",
            amount=Decimal("40.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 12),
        )

        progress = calculate_goal_progress(goal=goal, year=2026, month=5)

        self.assertEqual(progress["current_amount"], Decimal("120.00"))
        self.assertEqual(progress["remaining_amount"], Decimal("130.00"))
        self.assertEqual(progress["progress_percent"], Decimal("48.00"))

    def test_reduction_goal_progress_ignores_forecasted_ignored_and_canceled(self):
        """Nao deve somar despesas previstas, ignoradas ou canceladas."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        for status in (
            Transaction.PaymentStatus.FORECASTED,
            Transaction.PaymentStatus.IGNORED,
            Transaction.PaymentStatus.CANCELED,
        ):
            Transaction.objects.create(
                description=f"Delivery {status}",
                amount=Decimal("50.00"),
                transaction_type=Transaction.TransactionType.EXPENSE,
                status=status,
                account=self.spending_account,
                category=self.category,
                date=date(2026, 5, 10),
            )

        progress = calculate_goal_progress(goal=goal, year=2026, month=5)

        self.assertEqual(progress["current_amount"], Decimal("0.00"))

    def test_reduction_goal_counts_card_and_benefit_purchases_not_statement_payment(self):
        """Deve contar compra no cartao e no beneficio, mas nunca o pagamento da fatura."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        credit = Card.objects.create(
            name="Cartao Inter",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("3000.00"),
            statement_closing_day=10,
            statement_due_day=17,
            payment_account=self.spending_account,
        )
        benefit = Card.objects.create(
            name="Vale",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            balance=Decimal("500.00"),
        )
        for transaction_type, amount, status, card in (
            (Transaction.TransactionType.CARD_PURCHASE, "100.00", Transaction.PaymentStatus.PENDING, credit),
            (Transaction.TransactionType.BENEFIT_PURCHASE, "40.00", Transaction.PaymentStatus.PENDING, benefit),
            (Transaction.TransactionType.STATEMENT_PAYMENT, "100.00", Transaction.PaymentStatus.PAID, credit),
        ):
            Transaction.objects.create(
                description=transaction_type,
                amount=Decimal(amount),
                transaction_type=transaction_type,
                status=status,
                account=self.spending_account if card is credit and transaction_type == Transaction.TransactionType.STATEMENT_PAYMENT else None,
                card=card,
                category=self.category,
                date=date(2026, 5, 10),
            )

        progress = calculate_goal_progress(goal=goal, year=2026, month=5)

        self.assertEqual(progress["current_amount"], Decimal("140.00"))

    def test_update_monthly_goal_status_flags_risk_with_card_purchase(self):
        """Compra no cartao deve levar a meta de reducao para em risco."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("100.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        monthly_goal = create_monthly_goal_from_goal(goal=goal, year=2026, month=5)
        credit = Card.objects.create(
            name="Cartao Inter",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("3000.00"),
            statement_closing_day=10,
            statement_due_day=17,
            payment_account=self.spending_account,
        )
        Transaction.objects.create(
            description="Compra no cartao",
            amount=Decimal("90.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PENDING,
            card=credit,
            category=self.category,
            date=date(2026, 5, 10),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("90.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.AT_RISK)

    def test_reduction_goal_requires_year_and_month_for_progress(self):
        """Objetivo de reducao deve exigir periodo para calcular progresso."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )

        with self.assertRaises(ValidationError):
            calculate_goal_progress(goal=goal)

    def test_create_monthly_goal_from_goal_uses_goal_target_when_omitted(self):
        """Deve criar meta mensal usando valor alvo do objetivo por padrao."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("10000.00"),
            start_date=date(2026, 5, 1),
        )

        monthly_goal = create_monthly_goal_from_goal(
            goal=goal,
            year=2026,
            month=5,
        )

        self.assertIsNotNone(monthly_goal.id)
        self.assertEqual(monthly_goal.target_amount, Decimal("10000.00"))

    def test_update_monthly_goal_status_marks_accumulation_as_achieved(self):
        """Deve marcar meta de acumulo como atingida ao alcancar o valor alvo."""

        goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 5, 1),
        )
        goal.accounts.add(self.account, self.extra_account)
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("2000.00"),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("2000.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.ACHIEVED)

    def test_update_monthly_goal_status_marks_reduction_as_at_risk(self):
        """Deve marcar reducao como em risco ao consumir 80 porcento do limite."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("250.00"),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("200.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.AT_RISK)

    def test_update_monthly_goal_status_marks_reduction_as_missed(self):
        """Deve marcar reducao como nao atingida ao passar do limite."""

        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("250.00"),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal("260.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=5,
            target_amount=Decimal("250.00"),
        )

        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(updated.current_amount, Decimal("260.00"))
        self.assertEqual(updated.status, MonthlyGoal.Status.MISSED)

    def _reduction_monthly_goal(self, *, limit, spent):
        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal(limit),
            start_date=date(2026, 5, 1),
            category=self.category,
        )
        Transaction.objects.create(
            description="Delivery",
            amount=Decimal(spent),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.spending_account,
            category=self.category,
            date=date(2026, 5, 10),
        )
        return MonthlyGoal.objects.create(
            goal=goal, year=2026, month=5, target_amount=Decimal(limit)
        )

    def test_reduction_spending_equal_to_limit_is_at_risk(self):
        """Gasto igual ao limite ainda cabe no limite: em risco, nao excedido."""

        monthly_goal = self._reduction_monthly_goal(limit="250.00", spent="250.00")

        _, status = calculate_monthly_goal_status(monthly_goal)
        updated = update_monthly_goal_status(monthly_goal)

        self.assertEqual(status, MonthlyGoal.Status.AT_RISK)
        self.assertEqual(updated.status, MonthlyGoal.Status.AT_RISK)

    def test_reduction_spending_one_cent_above_limit_is_missed(self):
        monthly_goal = self._reduction_monthly_goal(limit="250.00", spent="250.01")

        _, status = calculate_monthly_goal_status(monthly_goal)

        self.assertEqual(status, MonthlyGoal.Status.MISSED)

    def test_reduction_spending_below_eighty_percent_is_on_track(self):
        monthly_goal = self._reduction_monthly_goal(limit="250.00", spent="199.99")

        _, status = calculate_monthly_goal_status(monthly_goal)

        self.assertEqual(status, MonthlyGoal.Status.ON_TRACK)

    def test_accumulation_reaching_target_is_still_achieved(self):
        goal = Goal.objects.create(
            name="Reserva",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 5, 1),
        )
        goal.accounts.set([self.account, self.extra_account])
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal, year=2026, month=5, target_amount=Decimal("2000.00")
        )

        _, status = calculate_monthly_goal_status(monthly_goal)

        self.assertEqual(status, MonthlyGoal.Status.ACHIEVED)


class CreateReductionGoalForCategoryTests(TestCase):
    """Garante o service de criacao de meta de reducao por categoria."""

    def setUp(self):
        """Cria categoria base."""

        self.category = Category.objects.create(name="Alimentacao")

    def test_creates_goal_and_monthly_goal(self):
        """Deve criar Goal de reducao e MonthlyGoal vinculados a categoria."""

        monthly_goal = create_reduction_goal_for_category(
            category=self.category,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        self.assertIsInstance(monthly_goal, MonthlyGoal)
        self.assertEqual(monthly_goal.goal.goal_type, Goal.GoalType.REDUCTION)
        self.assertEqual(monthly_goal.goal.category, self.category)
        self.assertEqual(monthly_goal.year, 2026)
        self.assertEqual(monthly_goal.month, 7)
        self.assertEqual(monthly_goal.target_amount, Decimal("500.00"))

    def test_reuses_existing_goal_for_same_category(self):
        """Segunda chamada nao deve criar novo Goal para a mesma categoria."""

        create_reduction_goal_for_category(
            category=self.category,
            year=2026,
            month=6,
            target_amount=Decimal("400.00"),
        )
        create_reduction_goal_for_category(
            category=self.category,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        self.assertEqual(
            Goal.objects.filter(
                goal_type=Goal.GoalType.REDUCTION, category=self.category
            ).count(),
            1,
        )
        self.assertEqual(MonthlyGoal.objects.count(), 2)

    def test_rejects_zero_amount(self):
        """Deve levantar ValidationError para valor zero."""

        with self.assertRaises(ValidationError):
            create_reduction_goal_for_category(
                category=self.category,
                year=2026,
                month=7,
                target_amount=Decimal("0.00"),
            )

    def test_rejects_negative_amount(self):
        """Deve levantar ValidationError para valor negativo."""

        with self.assertRaises(ValidationError):
            create_reduction_goal_for_category(
                category=self.category,
                year=2026,
                month=7,
                target_amount=Decimal("-100.00"),
            )

    def test_rejects_duplicate_monthly_goal(self):
        """Deve levantar erro ao criar MonthlyGoal duplicada para o mesmo mes."""

        create_reduction_goal_for_category(
            category=self.category,
            year=2026,
            month=7,
            target_amount=Decimal("400.00"),
        )

        with self.assertRaises(ValidationError) as ctx:
            create_reduction_goal_for_category(
                category=self.category,
                year=2026,
                month=7,
                target_amount=Decimal("500.00"),
            )

        self.assertFalse(hasattr(ctx.exception, "error_dict"))
        self.assertEqual(
            ctx.exception.messages,
            ["Já existe uma meta para Alimentacao em Julho/2026."],
        )
        self.assertEqual(MonthlyGoal.objects.count(), 1)


class InactiveReductionGoalTests(TestCase):
    """Garante reativacao do unico Goal de reducao inativo da categoria (D4-A)."""

    def setUp(self):
        self.category = Category.objects.create(name="Alimentacao")
        self.goal = Goal.objects.create(
            name="Limite - Alimentacao",
            goal_type=Goal.GoalType.REDUCTION,
            category=self.category,
            target_amount=Decimal("400.00"),
            start_date=date(2026, 1, 1),
            is_active=False,
        )

    def test_create_limit_reactivates_inactive_goal_without_second_goal(self):
        monthly_goal = create_reduction_goal_for_category(
            category=self.category,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        self.goal.refresh_from_db()
        self.assertTrue(self.goal.is_active)
        self.assertEqual(monthly_goal.goal_id, self.goal.pk)
        self.assertEqual(
            Goal.objects.filter(
                goal_type=Goal.GoalType.REDUCTION, category=self.category
            ).count(),
            1,
        )

    def test_create_limit_prefers_active_goal_and_keeps_inactive_untouched(self):
        active = Goal.objects.create(
            name="Limite ativo",
            goal_type=Goal.GoalType.REDUCTION,
            category=self.category,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 2, 1),
        )

        monthly_goal = create_reduction_goal_for_category(
            category=self.category,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        self.goal.refresh_from_db()
        self.assertEqual(monthly_goal.goal_id, active.pk)
        self.assertFalse(self.goal.is_active)


class MonthlyGoalRefreshTests(TestCase):
    """Garante calculo puro e recalculo em lote das metas mensais."""

    def setUp(self):
        self.category = Category.objects.create(name="Delivery")
        self.goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            category=self.category,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 5, 1),
        )
        self.monthly_goal = MonthlyGoal.objects.create(
            goal=self.goal, year=2026, month=5, target_amount=Decimal("300.00")
        )
        Transaction.objects.create(
            description="Pizza",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            category=self.category,
            date=date(2026, 5, 10),
        )

    def test_calculate_monthly_goal_status_does_not_write(self):
        current, status = calculate_monthly_goal_status(self.monthly_goal)

        self.assertEqual(current, Decimal("250.00"))
        self.assertEqual(status, MonthlyGoal.Status.AT_RISK)
        self.monthly_goal.refresh_from_db()
        self.assertEqual(self.monthly_goal.current_amount, Decimal("0.00"))
        self.assertEqual(self.monthly_goal.status, MonthlyGoal.Status.ON_TRACK)

    def test_refresh_monthly_goals_persists_only_requested_period(self):
        other = MonthlyGoal.objects.create(
            goal=self.goal, year=2026, month=6, target_amount=Decimal("300.00")
        )

        count = refresh_monthly_goals(year=2026, month=5)

        self.monthly_goal.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertEqual(self.monthly_goal.status, MonthlyGoal.Status.AT_RISK)
        self.assertEqual(other.current_amount, Decimal("0.00"))

    def test_refresh_monthly_goals_is_idempotent(self):
        refresh_monthly_goals(year=2026, month=5)
        refresh_monthly_goals(year=2026, month=5)

        self.monthly_goal.refresh_from_db()
        self.assertEqual(self.monthly_goal.current_amount, Decimal("250.00"))
        self.assertEqual(MonthlyGoal.objects.count(), 1)


class ClosedMonthAccumulationTests(TestCase):
    """Acumulacao de mes fechado e snapshot; nunca recalculada (ADR-016)."""

    def setUp(self):
        patcher = mock.patch(
            "goals.services.timezone.localdate", return_value=date(2026, 6, 15)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Reserva",
            institution=institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("2500.00"),
        )
        self.goal = Goal.objects.create(
            name="Reserva de emergencia",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("2000.00"),
            start_date=date(2026, 1, 1),
        )
        self.goal.accounts.add(self.account)

    def _snapshot(self, *, month):
        return MonthlyGoal.objects.create(
            goal=self.goal,
            year=2026,
            month=month,
            target_amount=Decimal("2000.00"),
            current_amount=Decimal("2500.00"),
            status=MonthlyGoal.Status.ACHIEVED,
        )

    def test_update_keeps_closed_month_after_balance_change(self):
        monthly_goal = self._snapshot(month=3)
        self.account.balance = Decimal("100.00")
        self.account.save(update_fields=["balance"])

        update_monthly_goal_status(monthly_goal)

        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.current_amount, Decimal("2500.00"))
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.ACHIEVED)

    def test_refresh_keeps_closed_month_after_balance_change(self):
        monthly_goal = self._snapshot(month=3)
        self.account.balance = Decimal("100.00")
        self.account.save(update_fields=["balance"])

        refresh_monthly_goals(year=2026, month=3)

        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.current_amount, Decimal("2500.00"))
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.ACHIEVED)

    def test_current_month_uses_current_balance(self):
        monthly_goal = MonthlyGoal.objects.create(
            goal=self.goal, year=2026, month=6, target_amount=Decimal("2000.00")
        )
        self.account.balance = Decimal("100.00")
        self.account.save(update_fields=["balance"])

        update_monthly_goal_status(monthly_goal)

        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.current_amount, Decimal("100.00"))
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.ON_TRACK)

    def test_explicit_today_decides_which_month_is_closed(self):
        monthly_goal = MonthlyGoal.objects.create(
            goal=self.goal, year=2026, month=6, target_amount=Decimal("2000.00")
        )

        update_monthly_goal_status(monthly_goal, today=date(2026, 7, 1))

        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.current_amount, Decimal("0.00"))

    def test_reduction_of_closed_month_is_still_recalculated(self):
        category = Category.objects.create(name="Delivery")
        goal = Goal.objects.create(
            name="Reduzir delivery",
            goal_type=Goal.GoalType.REDUCTION,
            category=category,
            target_amount=Decimal("300.00"),
            start_date=date(2026, 1, 1),
        )
        monthly_goal = MonthlyGoal.objects.create(
            goal=goal, year=2026, month=3, target_amount=Decimal("300.00")
        )
        Transaction.objects.create(
            description="Pizza",
            amount=Decimal("350.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            category=category,
            date=date(2026, 3, 31),
        )

        update_monthly_goal_status(monthly_goal)

        monthly_goal.refresh_from_db()
        self.assertEqual(monthly_goal.current_amount, Decimal("350.00"))
        self.assertEqual(monthly_goal.status, MonthlyGoal.Status.MISSED)


class SingleCurrencyAccumulationTests(TestCase):
    """Objetivo de acumulacao nao soma moedas diferentes (ADR-016)."""

    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.brl = FinancialAccount.objects.create(
            name="Real",
            institution=institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("1000.00"),
        )
        self.brl2 = FinancialAccount.objects.create(
            name="Real 2",
            institution=institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        self.usd = FinancialAccount.objects.create(
            name="Dolar",
            institution=institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("300.00"),
            currency=FinancialAccount.Currency.USD,
        )

    def test_validate_accepts_single_currency(self):
        validate_goal_accounts_currency([self.brl, self.brl2])
        validate_goal_accounts_currency([])

    def test_validate_rejects_mixed_currencies_with_readable_message(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_goal_accounts_currency([self.brl, self.usd])

        self.assertIn("uma unica moeda", " ".join(ctx.exception.messages))

    def test_progress_with_mixed_currencies_raises_instead_of_summing(self):
        goal = Goal.objects.create(
            name="Misto",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount=Decimal("1000.00"),
            start_date=date(2026, 1, 1),
        )
        goal.accounts.add(self.brl, self.usd)

        with self.assertRaises(ValidationError):
            calculate_goal_progress(goal=goal)
