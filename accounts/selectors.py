"""Seletores para leitura de contas financeiras."""

from collections import defaultdict
from decimal import Decimal

from .models import FinancialAccount


def get_active_accounts():
    """Lista contas financeiras ativas com instituicao carregada."""

    return (
        FinancialAccount.objects.filter(is_active=True)
        .select_related("institution")
        .order_by("currency", "institution__name", "name")
    )


def get_accounts_by_currency(*, currency: str):
    """Lista contas financeiras por moeda."""

    return (
        FinancialAccount.objects.filter(currency=currency)
        .select_related("institution")
        .order_by("-is_active", "institution__name", "name")
    )


def get_account_summary() -> list[dict]:
    """Agrupa contas por moeda e calcula totais de saldo."""

    accounts = (
        FinancialAccount.objects.select_related("institution")
        .order_by("currency", "institution__name", "name")
    )
    currency_labels = dict(FinancialAccount.Currency.choices)
    grouped_accounts = defaultdict(list)

    for account in accounts:
        grouped_accounts[account.currency].append(account)

    return [
        {
            "currency": currency,
            "currency_label": currency_labels.get(currency, currency),
            "accounts": currency_accounts,
            "total_balance": sum(
                (account.balance for account in currency_accounts),
                Decimal("0.00"),
            ),
            "active_count": sum(
                1 for account in currency_accounts if account.is_active
            ),
            "inactive_count": sum(
                1 for account in currency_accounts if not account.is_active
            ),
        }
        for currency, currency_accounts in grouped_accounts.items()
    ]
