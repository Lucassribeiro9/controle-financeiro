"""Cenarios de dados realistas para validar a geracao de insights."""

from datetime import date
from decimal import Decimal

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction

PAID = Transaction.PaymentStatus.PAID
EXPENSE = Transaction.TransactionType.EXPENSE


def build_realistic_month(*, year, month):
    """Cria um mes com gastos que qualificam e que nao devem gerar insight.

    Qualificam: Mercado (3 despesas pagas) e Transporte (2 despesas pagas).
    Nao qualificam: Lazer (previsto, cancelado e pendente), Saude (apenas
    compra no cartao), despesas sem categoria, receita e gasto do mes seguinte.
    """

    institution = Institution.objects.create(name="Inter", code="077")
    account = FinancialAccount.objects.create(
        name="Conta corrente",
        institution=institution,
        account_type=FinancialAccount.AccountType.CHECKING,
        balance=Decimal("5000.00"),
    )
    card = Card.objects.create(
        name="Cartao Inter",
        institution=institution,
        card_type=Card.CardType.CREDIT,
        credit_limit=Decimal("3000.00"),
        statement_closing_day=10,
        statement_due_day=17,
        payment_account=account,
    )
    categories = {
        name: Category.objects.create(name=name)
        for name in ("Mercado", "Transporte", "Lazer", "Saude")
    }

    def add(description, amount, *, day=10, category=None, status=PAID,
            transaction_type=EXPENSE, when=None, with_card=False):
        return Transaction.objects.create(
            description=description,
            amount=Decimal(amount),
            transaction_type=transaction_type,
            status=status,
            account=None if with_card else account,
            card=card if with_card else None,
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
    add("Bar pendente", "90.00", category=categories["Lazer"],
        status=Transaction.PaymentStatus.PENDING)
    add("Farmacia no cartao", "120.00", category=categories["Saude"],
        transaction_type=Transaction.TransactionType.CARD_PURCHASE,
        status=Transaction.PaymentStatus.PENDING, with_card=True)
    add("Sem categoria 1", "25.00", day=5)
    add("Sem categoria 2", "35.00", day=6)
    add("Sem categoria 3", "45.00", day=7)
    add("Salario", "4000.00", day=5,
        transaction_type=Transaction.TransactionType.INCOME)

    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    add("Mercado do mes seguinte", "500.00", category=categories["Mercado"],
        when=date(next_year, next_month, 3))

    return categories
