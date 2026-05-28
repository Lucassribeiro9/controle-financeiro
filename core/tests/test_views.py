"""Testes das views do app core."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from institutions.models import Institution
from transactions.models import Transaction


class HomeViewTests(TestCase):
    """Garante que a home consome o contexto operacional."""

    def test_home_renders_with_empty_database(self):
        """A home deve renderizar sem excecao quando nao ha dados financeiros."""

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_home_context_includes_operational_contract(self):
        """A view deve expor as chaves principais retornadas pelo selector."""

        response = self.client.get(reverse("core:home"))

        for key in [
            "summary",
            "alerts",
            "pending_items",
            "quick_actions",
            "empty_states",
        ]:
            self.assertIn(key, response.context)

        self.assertEqual(
            response.context["summary"]["realized"]["income"],
            Decimal("0.00"),
        )
        self.assertEqual(response.context["alerts"], [])
        self.assertEqual(response.context["pending_items"], [])
        self.assertTrue(response.context["empty_states"]["summary"]["is_empty"])

    def test_home_displays_empty_month_summary(self):
        """Banco vazio deve exibir resumo zerado de forma compreensivel."""

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Resumo financeiro do mês")
        self.assertContains(response, "Sem lançamentos")
        self.assertContains(response, "Nenhum lancamento neste mes")
        self.assertContains(response, "R$ 0,00")

    def test_home_displays_month_summary_with_real_transactions(self):
        """A home deve separar valores realizados, pendentes e previstos."""

        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        period = self.client.get(reverse("core:home")).context["summary"]["period"]
        year = period["year"]
        month = period["month"]

        Transaction.objects.create(
            description="Salario",
            amount=Decimal("5000.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            date=date(year, month, 5),
        )
        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("450.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            date=date(year, month, 6),
        )
        Transaction.objects.create(
            description="Internet",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PENDING,
            account=account,
            date=date(year, month, 10),
        )
        Transaction.objects.create(
            description="Assinatura prevista",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.FORECASTED,
            account=account,
            date=date(year, month, 15),
        )

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Realizado")
        self.assertContains(response, "Pendente")
        self.assertContains(response, "Previsto")
        self.assertContains(response, "R$ 5.000,00")
        self.assertContains(response, "R$ 450,00")
        self.assertContains(response, "R$ 4.550,00")
        self.assertContains(response, "-R$ 120,00")
        self.assertContains(response, "-R$ 50,00")
