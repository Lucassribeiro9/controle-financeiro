"""Tests dos selectors do app categories."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from categories.selectors import get_categories_with_monthly_spent
from goals.models import Goal, MonthlyGoal
from institutions.models import Institution
from transactions.models import Transaction


class CategoryMonthlySpentSelectorTests(TestCase):
    """Garante o calculo correto de gasto mensal por categoria."""

    def setUp(self):
        """Cria estrutura base: instituicao, conta e categorias."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.cat_food = Category.objects.create(name="Alimentacao")
        self.cat_transport = Category.objects.create(name="Transporte")
        self.reference_date = date(2026, 7, 1)

    def test_calculates_monthly_expense_correctly(self):
        """Deve somar despesas do mes para a categoria."""

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("150.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 10),
        )
        Transaction.objects.create(
            description="Padaria",
            amount=Decimal("30.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 15),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.monthly_spent, Decimal("180.00"))

    def test_ignores_income_transactions(self):
        """Nao deve incluir receitas no calculo de gasto."""

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 5),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.monthly_spent, Decimal("0.00"))

    def test_ignores_canceled_ignored_forecasted_statuses(self):
        """Nao deve incluir transacoes canceladas, ignoradas ou previstas."""

        for status in [
            Transaction.PaymentStatus.CANCELED,
            Transaction.PaymentStatus.IGNORED,
            Transaction.PaymentStatus.FORECASTED,
        ]:
            Transaction.objects.create(
                description=f"Despesa {status}",
                amount=Decimal("100.00"),
                transaction_type=Transaction.TransactionType.EXPENSE,
                status=status,
                account=self.account,
                category=self.cat_food,
                date=date(2026, 7, 10),
            )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.monthly_spent, Decimal("0.00"))

    def test_ignores_transactions_from_other_months(self):
        """Nao deve incluir despesas de meses anteriores ou futuros."""

        Transaction.objects.create(
            description="Despesa junho",
            amount=Decimal("200.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 6, 28),
        )
        Transaction.objects.create(
            description="Despesa agosto",
            amount=Decimal("300.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 8, 1),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.monthly_spent, Decimal("0.00"))

    def test_category_without_transactions_returns_zero(self):
        """Categoria sem transacoes deve retornar zero, nao None."""

        result = get_categories_with_monthly_spent(self.reference_date)
        transport = next(c for c in result if c.name == "Transporte")

        self.assertEqual(transport.monthly_spent, Decimal("0.00"))

    def test_includes_card_purchase_and_benefit_purchase(self):
        """Deve incluir compras no cartao e beneficio como despesas."""

        from cards.models import Card

        credit_card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )
        benefit_card = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("300.00"),
            balance=Decimal("300.00"),
        )

        Transaction.objects.create(
            description="Restaurante cartao",
            amount=Decimal("80.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            status=Transaction.PaymentStatus.PAID,
            card=credit_card,
            category=self.cat_food,
            date=date(2026, 7, 12),
        )
        Transaction.objects.create(
            description="VA almoco",
            amount=Decimal("25.00"),
            transaction_type=Transaction.TransactionType.BENEFIT_PURCHASE,
            status=Transaction.PaymentStatus.PAID,
            card=benefit_card,
            category=self.cat_food,
            date=date(2026, 7, 12),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.monthly_spent, Decimal("105.00"))

    def test_selector_annotates_limit_amount(self):
        """Deve anotar o limit_amount correto vindo do MonthlyGoal."""
        goal = Goal.objects.create(
            name="Limite Lazer",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date(2026, 7, 1),
            category=self.cat_transport,
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=7,
            target_amount=Decimal("400.00"),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        transport = next(c for c in result if c.name == "Transporte")

        self.assertEqual(transport.limit_amount, Decimal("400.00"))

    def test_limit_status_calculates_ok(self):
        """Garante status 'ok' quando o gasto esta abaixo de 80% do limite."""
        goal = Goal.objects.create(
            name="Limite Alimentacao",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date(2026, 7, 1),
            category=self.cat_food,
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        # 399.00 / 500.00 = 79.8% (< 80%)
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("399.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 10),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.limit_status, "ok")
        self.assertEqual(food.limit_progress_percent, Decimal("79.8"))

    def test_limit_status_calculates_at_risk(self):
        """Garante status 'at_risk' quando o gasto esta entre 80% e < 100% do limite."""
        goal = Goal.objects.create(
            name="Limite Alimentacao",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date(2026, 7, 1),
            category=self.cat_food,
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        # 400.00 / 500.00 = 80.0% (entre 80% e < 100%)
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("400.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 10),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.limit_status, "at_risk")
        self.assertEqual(food.limit_progress_percent, Decimal("80.0"))

    def test_limit_status_calculates_exceeded(self):
        """Garante status 'exceeded' quando o gasto esta >= 100% do limite."""
        goal = Goal.objects.create(
            name="Limite Alimentacao",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date(2026, 7, 1),
            category=self.cat_food,
        )
        MonthlyGoal.objects.create(
            goal=goal,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )

        # 500.00 / 500.00 = 100.0% (>= 100%)
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("500.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 10),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.limit_status, "exceeded")
        self.assertEqual(food.limit_progress_percent, Decimal("100.0"))

    def test_limit_status_is_none_when_no_limit(self):
        """Garante que limit_amount e limit_status sao None quando nao ha limite cadastrado."""
        result = get_categories_with_monthly_spent(self.reference_date)
        transport = next(c for c in result if c.name == "Transporte")

        self.assertIsNone(transport.limit_amount)
        self.assertIsNone(transport.limit_status)
        self.assertIsNone(transport.limit_progress_percent)

