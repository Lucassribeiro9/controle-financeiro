"""Cenarios de dados de exemplo, sempre criados pelos services do projeto."""

from datetime import date
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from accounts.models import FinancialAccount
from cards.models import Card, CardStatement
from cards.services import auto_close_due_statements, pay_statement
from categories.models import Category
from goals.models import Goal, MonthlyGoal
from goals.services import (
    create_monthly_goal_from_goal,
    create_reduction_goal_for_category,
    update_monthly_goal_status,
)
from imports.models import ImportedTransaction
from insights.models import IgnoredPattern, Insight
from insights.services import generate_monthly_insights
from installments.models import InstallmentPlan
from institutions.models import Institution
from recurrences.models import Recurrence
from recurrences.services import generate_monthly_recurrences_forecasts
from transactions.models import Transaction, Transfer
from transactions.services import (
    create_transaction,
    create_transaction_by_payment_method,
    create_transfer,
)

PAID = Transaction.PaymentStatus.PAID
PENDING = Transaction.PaymentStatus.PENDING
INCOME = Transaction.TransactionType.INCOME
EXPENSE = Transaction.TransactionType.EXPENSE


def _save_validated(instance):
    """Valida e grava models que nao tem service de criacao proprio."""

    instance.full_clean()
    instance.save()
    return instance


def _shift_month(*, year, month, offset):
    """Devolve (ano, mes) deslocado em `offset` meses."""

    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1


def reset_financial_data():
    """Apaga todos os dados financeiros, preservando usuarios."""

    with db_transaction.atomic():
        Insight.objects.all().delete()
        IgnoredPattern.objects.all().delete()
        MonthlyGoal.objects.all().delete()
        Goal.objects.all().delete()
        ImportedTransaction.objects.all().delete()
        Transfer.objects.all().delete()
        Transaction.objects.all().delete()
        InstallmentPlan.objects.all().delete()
        Recurrence.objects.all().delete()
        CardStatement.objects.all().delete()
        Card.objects.all().delete()
        FinancialAccount.objects.all().delete()
        Category.objects.filter(parent__isnull=False).delete()
        Category.objects.all().delete()
        Institution.objects.all().delete()


def has_financial_data():
    """Indica se ja existe algum dado financeiro no banco."""

    return any(
        model.objects.exists()
        for model in (Institution, FinancialAccount, Card, Category, Transaction)
    )


def build_demo_data(*, today=None):
    """Cria 3 meses de dados coerentes e deterministicos para uso em dev.

    Valores e datas so dependem do dia atual, sem aleatoriedade. Itens com
    data futura entram como pendentes e o restante como pago.
    """

    today = today or timezone.localdate()
    months = [
        _shift_month(year=today.year, month=today.month, offset=offset)
        for offset in (-2, -1, 0)
    ]

    with db_transaction.atomic():
        ctx = _create_base_records(today=today, months=months)
        _create_monthly_transactions(ctx=ctx, today=today, months=months)
        _create_installment_purchase(ctx=ctx, months=months)
        _create_recurrences_and_forecasts(ctx=ctx, months=months)
        _settle_statements(today=today, months=months)
        _create_goals(ctx=ctx, months=months)
        for year, month in months:
            generate_monthly_insights(year=year, month=month)

    return ctx


def _create_base_records(*, today, months):
    """Cria instituicao, contas, cartao e categorias."""

    institution = _save_validated(Institution(name="Banco Demo", code="999"))

    def account(name, account_type, balance):
        return _save_validated(
            FinancialAccount(
                name=name,
                institution=institution,
                account_type=account_type,
                balance=Decimal(balance),
            )
        )

    checking = account("Conta corrente", FinancialAccount.AccountType.CHECKING, "3000.00")
    savings = account("Poupança", FinancialAccount.AccountType.SAVINGS, "8000.00")
    benefit = account("Vale benefício", FinancialAccount.AccountType.BENEFIT, "0.00")

    card = _save_validated(
        Card(
            name="Cartão Demo",
            institution=institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("4000.00"),
            statement_closing_day=20,
            statement_due_day=28,
            payment_account=checking,
        )
    )

    categories = {}
    for name in ("Moradia", "Alimentação", "Transporte", "Lazer", "Saúde"):
        categories[name] = _save_validated(Category(name=name))
    for name, parent in (
        ("Mercado", "Alimentação"),
        ("Restaurantes", "Alimentação"),
        ("Combustível", "Transporte"),
    ):
        categories[name] = _save_validated(
            Category(name=name, parent=categories[parent])
        )

    return {
        "institution": institution,
        "checking": checking,
        "savings": savings,
        "benefit": benefit,
        "card": card,
        "categories": categories,
    }


def _create_monthly_transactions(*, ctx, today, months):
    """Cria receitas, despesas, compras no cartao e transferencias."""

    categories = ctx["categories"]

    def status_for(when):
        return PAID if when <= today else PENDING

    for index, (year, month) in enumerate(months):
        extra = Decimal(index * 15)

        def day(number):
            return date(year, month, number)

        create_transaction(
            description="Salário",
            amount=Decimal("4500.00"),
            transaction_type=INCOME,
            date=day(5),
            account=ctx["checking"],
            status=status_for(day(5)),
        )
        create_transaction(
            description="Vale benefício",
            amount=Decimal("600.00"),
            transaction_type=INCOME,
            date=day(1),
            account=ctx["benefit"],
            status=status_for(day(1)),
        )
        if index < 2:
            create_transaction(
                description="Aluguel",
                amount=Decimal("1200.00"),
                transaction_type=EXPENSE,
                date=day(6),
                account=ctx["checking"],
                category=categories["Moradia"],
                status=status_for(day(6)),
            )
        for number, description, amount in (
            (3, "Supermercado", Decimal("280.00") + extra),
            (10, "Feira", Decimal("90.50") + extra),
            (17, "Padaria", Decimal("45.00") + extra),
        ):
            create_transaction(
                description=description,
                amount=amount,
                transaction_type=EXPENSE,
                date=day(number),
                account=ctx["checking"],
                category=categories["Mercado"],
                status=status_for(day(number)),
            )
        create_transaction(
            description="Combustível",
            amount=Decimal("210.00") + extra,
            transaction_type=EXPENSE,
            date=day(12),
            account=ctx["checking"],
            category=categories["Combustível"],
            status=status_for(day(12)),
        )
        create_transaction(
            description="Almoço com vale",
            amount=Decimal("120.00"),
            transaction_type=EXPENSE,
            date=day(11),
            account=ctx["benefit"],
            category=categories["Restaurantes"],
            status=status_for(day(11)),
        )
        for number, description, amount, category in (
            (4, "Jantar", Decimal("85.00"), "Restaurantes"),
            (9, "Cinema", Decimal("60.00"), "Lazer"),
            (16, "Farmácia", Decimal("120.00"), "Saúde"),
        ):
            create_transaction_by_payment_method(
                payment_method="credit",
                description=description,
                amount=amount,
                transaction_type=Transaction.TransactionType.CARD_PURCHASE,
                date=day(number),
                card=ctx["card"],
                category=categories[category],
            )
        create_transfer(
            description="Reserva do mês",
            amount=Decimal("500.00"),
            from_account=ctx["checking"],
            destination_account=ctx["savings"],
            date=day(7),
        )

    year, month = months[-1]
    for number, description in ((27, "Internet"), (28, "Conta de luz")):
        create_transaction(
            description=description,
            amount=Decimal("110.00"),
            transaction_type=EXPENSE,
            date=date(year, month, number),
            account=ctx["checking"],
            category=categories["Moradia"],
            status=PENDING,
        )


def _create_installment_purchase(*, ctx, months):
    """Cria uma compra parcelada em 6x a partir do primeiro mes."""

    year, month = months[0]
    create_transaction_by_payment_method(
        payment_method="credit",
        description="Notebook",
        amount=Decimal("1800.00"),
        transaction_type=Transaction.TransactionType.CARD_PURCHASE,
        date=date(year, month, 7),
        card=ctx["card"],
        category=ctx["categories"]["Lazer"],
        total_installments=6,
    )


def _create_recurrences_and_forecasts(*, ctx, months):
    """Cria recorrencias e gera previsoes do mes atual e do seguinte."""

    for name, day, frequency, kind, amount, account, card in (
        ("Aluguel", 6, "monthly", "fixed_bill", "1200.00", ctx["checking"], None),
        ("Streaming", 12, "monthly", "subscription", "39.90", None, ctx["card"]),
        ("Academia", 10, "monthly", "subscription", "99.90", None, ctx["card"]),
    ):
        _save_validated(
            Recurrence(
                name=name,
                expected_day=day,
                frequency=frequency,
                recurrence_type=kind,
                expected_amount=Decimal(amount),
                account=account,
                card=card,
            )
        )

    year, month = months[-1]
    next_year, next_month = _shift_month(year=year, month=month, offset=1)
    generate_monthly_recurrences_forecasts(year=year, month=month)
    generate_monthly_recurrences_forecasts(year=next_year, month=next_month)


def _settle_statements(*, today, months):
    """Fecha as faturas vencidas e paga a do primeiro mes."""

    auto_close_due_statements(today=today)
    year, month = months[0]
    statement = CardStatement.objects.get(year=year, month=month)
    pay_statement(statement=statement)


def _create_goals(*, ctx, months):
    """Cria objetivos de acumulacao e de reducao com metas mensais."""

    first_year, first_month = months[0]
    start_date = date(first_year, first_month, 1)

    for name, target in (("Reserva de emergência", "20000.00"), ("Viagem", "5000.00")):
        goal = _save_validated(
            Goal(
                name=name,
                goal_type=Goal.GoalType.ACCUMULATION,
                target_amount=Decimal(target),
                start_date=start_date,
            )
        )
        goal.accounts.add(ctx["savings"])
        for year, month in months:
            monthly_goal = create_monthly_goal_from_goal(
                goal=goal, year=year, month=month
            )
            update_monthly_goal_status(monthly_goal)

    for category_name, target in (
        ("Mercado", "800.00"),
        ("Restaurantes", "300.00"),
        ("Lazer", "150.00"),
    ):
        for year, month in months:
            monthly_goal = create_reduction_goal_for_category(
                category=ctx["categories"][category_name],
                year=year,
                month=month,
                target_amount=Decimal(target),
            )
            update_monthly_goal_status(monthly_goal)


def build_realistic_month(*, year, month):
    """Cria um mes com gastos que qualificam e que nao devem gerar insight.

    Qualificam: Mercado (3 despesas pagas), Transporte (2 despesas pagas),
    Lazer (despesa pendente) e Saude (compra pendente no cartao).
    Nao qualificam: lancamentos previstos ou cancelados, despesas sem
    categoria, receita e gasto do mes seguinte.
    """

    institution = _save_validated(Institution(name="Inter", code="077"))
    account = _save_validated(
        FinancialAccount(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("5000.00"),
        )
    )
    card = _save_validated(
        Card(
            name="Cartao Inter",
            institution=institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("3000.00"),
            statement_closing_day=10,
            statement_due_day=17,
            payment_account=account,
        )
    )
    categories = {
        name: _save_validated(Category(name=name))
        for name in ("Mercado", "Transporte", "Lazer", "Saude")
    }

    def add(description, amount, *, day=10, category=None, status=PAID,
            transaction_type=EXPENSE, when=None):
        return create_transaction(
            description=description,
            amount=Decimal(amount),
            transaction_type=transaction_type,
            status=status,
            account=account,
            category=category,
            date=when or date(year, month, day),
        )

    add("Supermercado", "300.00", day=2, category=categories["Mercado"])
    add("Feira", "80.50", day=9, category=categories["Mercado"])
    add("Padaria", "40.00", day=16, category=categories["Mercado"])
    add("Combustivel", "200.00", day=4, category=categories["Transporte"])
    add("Aplicativo", "30.00", day=18, category=categories["Transporte"])
    add("Cinema previsto", "60.00", category=categories["Lazer"],
        status=Transaction.PaymentStatus.FORECASTED)
    add("Show cancelado", "150.00", category=categories["Lazer"],
        status=Transaction.PaymentStatus.CANCELED)
    add("Bar pendente", "90.00", category=categories["Lazer"], status=PENDING)
    create_transaction_by_payment_method(
        payment_method="credit",
        description="Farmacia no cartao",
        amount=Decimal("120.00"),
        transaction_type=Transaction.TransactionType.CARD_PURCHASE,
        date=date(year, month, 10),
        card=card,
        category=categories["Saude"],
    )
    add("Sem categoria 1", "25.00", day=5)
    add("Sem categoria 2", "35.00", day=6)
    add("Sem categoria 3", "45.00", day=7)
    add("Salario", "4000.00", day=5, transaction_type=INCOME)

    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    add("Mercado do mes seguinte", "500.00", category=categories["Mercado"],
        when=date(next_year, next_month, 3))

    return categories
