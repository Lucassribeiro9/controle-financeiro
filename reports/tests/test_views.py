"""Tests das views do app reports."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction


class MonthlyDashboardViewTests(TestCase):
    """Garante o carregamento do dashboard mensal."""

    def setUp(self):
        """Cria dados base para o dashboard."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")

    def test_monthly_dashboard_view_returns_success(self):
        """Deve renderizar o dashboard mensal."""

        response = self.client.get(
            reverse(
                "reports:monthly-dashboard",
                kwargs={"year": 2026, "month": 5},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/monthly_dashboard.html")
        self.assertContains(response, "Dashboard financeiro")

    def test_monthly_dashboard_view_uses_selector_context(self):
        """Deve exibir totais calculados pelos selectors."""

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            date=date(2026, 5, 5),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("300.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=self.account,
            category=self.category,
            date=date(2026, 5, 10),
        )

        response = self.client.get(
            reverse(
                "reports:monthly-dashboard",
                kwargs={"year": 2026, "month": 5},
            )
        )

        self.assertEqual(response.context["income_total"], Decimal("5000.00"))
        self.assertEqual(response.context["expense_total"], Decimal("300.00"))
        self.assertEqual(response.context["monthly_balance"], Decimal("4700.00"))
        self.assertContains(response, "Alimentacao")
