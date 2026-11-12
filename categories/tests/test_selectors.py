"""Tests dos selectors do app categories."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from categories.models import Category
from categories.selectors import (
    get_categories_for_list,
    get_categories_with_monthly_spent,
    get_categories_at_risk,
)
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
        """Garante status 'exceeded' somente quando o gasto passa de 100% do limite."""
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

        # 500.01 / 500.00 > 100%
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("500.01"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 10),
        )

        result = get_categories_with_monthly_spent(self.reference_date)
        food = next(c for c in result if c.name == "Alimentacao")

        self.assertEqual(food.limit_status, "exceeded")

    def test_limit_status_is_none_when_no_limit(self):
        """Garante que limit_amount e limit_status sao None quando nao ha limite cadastrado."""
        result = get_categories_with_monthly_spent(self.reference_date)
        transport = next(c for c in result if c.name == "Transporte")

        self.assertIsNone(transport.limit_amount)
        self.assertIsNone(transport.limit_status)
        self.assertIsNone(transport.limit_progress_percent)

    def test_get_categories_at_risk_returns_only_above_80_percent(self):
        """get_categories_at_risk deve retornar apenas categorias >= 80% do limite."""
        goal_food = Goal.objects.create(
            name="Limite Alimentacao",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("500.00"),
            start_date=date(2026, 7, 1),
            category=self.cat_food,
        )
        MonthlyGoal.objects.create(
            goal=goal_food,
            year=2026,
            month=7,
            target_amount=Decimal("500.00"),
        )
        
        goal_transport = Goal.objects.create(
            name="Limite Transporte",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal("200.00"),
            start_date=date(2026, 7, 1),
            category=self.cat_transport,
        )
        MonthlyGoal.objects.create(
            goal=goal_transport,
            year=2026,
            month=7,
            target_amount=Decimal("200.00"),
        )

        # Alimentacao gastou 400.00 (80% - at_risk) -> deve retornar
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("400.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_food,
            date=date(2026, 7, 10),
        )

        # Transporte gastou 100.00 (50% - ok) -> nao deve retornar
        Transaction.objects.create(
            description="Combustivel",
            amount=Decimal("100.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.cat_transport,
            date=date(2026, 7, 10),
        )

        result = get_categories_at_risk(self.reference_date)
        result_list = list(result)

        self.assertEqual(len(result_list), 1)
        self.assertEqual(result_list[0].name, "Alimentacao")




class CategoryLimitRuleTests(TestCase):
    """Garante a regra unica de limite: <80% ok, 80-100% risco, >100% excedido."""

    def setUp(self):
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=Institution.objects.create(name="Inter", code="077"),
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")
        self.reference_date = date(2026, 7, 1)

    def _goal(self, *, target="500.00", is_active=True, category=None):
        return Goal.objects.create(
            name="Limite",
            goal_type=Goal.GoalType.REDUCTION,
            target_amount=Decimal(target),
            start_date=date(2026, 7, 1),
            category=category or self.category,
            is_active=is_active,
        )

    def _monthly(self, goal, target="500.00"):
        return MonthlyGoal.objects.create(
            goal=goal, year=2026, month=7, target_amount=Decimal(target)
        )

    def _spend(self, amount):
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal(amount),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 7, 10),
        )

    def _category(self):
        return get_categories_with_monthly_spent(self.reference_date).get(
            pk=self.category.pk
        )

    def test_spending_equal_to_limit_is_at_risk(self):
        self._monthly(self._goal())
        self._spend("500.00")

        category = self._category()

        self.assertEqual(category.limit_status, "at_risk")
        self.assertEqual(category.limit_progress_percent, Decimal("100"))

    def test_spending_above_limit_is_exceeded(self):
        self._monthly(self._goal())
        self._spend("500.01")

        self.assertEqual(self._category().limit_status, "exceeded")

    def test_category_at_exact_limit_is_listed_as_at_risk(self):
        self._monthly(self._goal())
        self._spend("500.00")

        result = get_categories_at_risk(self.reference_date)

        self.assertEqual([c.pk for c in result], [self.category.pk])

    def test_inactive_goal_monthly_goal_is_not_displayed_as_limit(self):
        self._monthly(self._goal(is_active=False))
        self._spend("450.00")

        category = self._category()

        self.assertIsNone(category.limit_amount)
        self.assertIsNone(category.limit_status)
        self.assertEqual(list(get_categories_at_risk(self.reference_date)), [])

    def test_active_goal_wins_over_inactive_one_in_same_month(self):
        inactive = self._goal(target="100.00", is_active=False)
        active = self._goal(target="500.00")
        self._monthly(inactive, target="100.00")
        self._monthly(active, target="500.00")

        self.assertEqual(self._category().limit_amount, Decimal("500.00"))

    def test_lowest_goal_id_wins_among_active_goals(self):
        first = self._goal(target="300.00")
        second = self._goal(target="900.00")
        # criada fora de ordem para nao depender da ordem de insercao
        self._monthly(second, target="900.00")
        self._monthly(first, target="300.00")

        self.assertEqual(self._category().limit_amount, Decimal("300.00"))


class CategoryListSelectorTests(TestCase):
    """Garante children_count e gasto corretos na listagem de categorias."""

    def setUp(self):
        """Cria instituicao, conta e data de referencia."""

        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.reference_date = date(2026, 7, 1)

    def _expense(self, category, amount, day=10, month=7):
        return Transaction.objects.create(
            description="Despesa",
            amount=Decimal(amount),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=category,
            date=date(2026, month, day),
        )

    def _get(self, category):
        result = get_categories_for_list(self.reference_date)
        return next(c for c in result if c.pk == category.pk)

    def test_parent_with_two_children_counts_two_without_multiplying_spent(self):
        """Pai com 2 filhos e 3 despesas deve contar 2 e somar 175."""

        parent = Category.objects.create(name="Moradia")
        Category.objects.create(name="Aluguel", parent=parent)
        Category.objects.create(name="Condominio", parent=parent)
        self._expense(parent, "100.00", day=5)
        self._expense(parent, "50.00", day=6)
        self._expense(parent, "25.00", day=7)

        result = self._get(parent)

        self.assertEqual(result.children_count, 2)
        self.assertEqual(result.monthly_spent, Decimal("175.00"))

    def test_parent_with_one_child_counts_one_with_many_expenses(self):
        """Pai com 1 filho e varias despesas (inclusive de outro mes) conta 1."""

        parent = Category.objects.create(name="Moradia")
        Category.objects.create(name="Aluguel", parent=parent)
        self._expense(parent, "100.00", day=5)
        self._expense(parent, "50.00", day=6)
        self._expense(parent, "70.00", day=6, month=6)

        result = self._get(parent)

        self.assertEqual(result.children_count, 1)
        self.assertEqual(result.monthly_spent, Decimal("150.00"))

    def test_category_without_children_counts_zero(self):
        """Categoria sem filhos deve ter children_count 0 e gasto correto."""

        category = Category.objects.create(name="Lazer")
        self._expense(category, "40.00")
        self._expense(category, "10.00", day=11)

        result = self._get(category)

        self.assertEqual(result.children_count, 0)
        self.assertEqual(result.monthly_spent, Decimal("50.00"))

    def test_monthly_spent_does_not_depend_on_children_count(self):
        """O gasto do pai deve ser igual com 0, 1 e 2 subcategorias."""

        spent = []
        for n in range(3):
            parent = Category.objects.create(name=f"Pai {n}")
            for i in range(n):
                Category.objects.create(name=f"Filho {n}-{i}", parent=parent)
            self._expense(parent, "100.00", day=5)
            self._expense(parent, "50.00", day=6)
            spent.append(self._get(parent).monthly_spent)

        self.assertEqual(spent, [Decimal("150.00")] * 3)

    def test_orders_by_parent_name_then_name(self):
        """Deve preservar a ordenacao por nome do pai e depois nome."""

        parent = Category.objects.create(name="Moradia")
        Category.objects.create(name="Zeta", parent=parent)
        Category.objects.create(name="Aluguel", parent=parent)

        names = [c.name for c in get_categories_for_list(self.reference_date)]

        self.assertLess(names.index("Aluguel"), names.index("Zeta"))
