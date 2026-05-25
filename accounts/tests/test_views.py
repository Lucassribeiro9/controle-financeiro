"""Tests das views do app accounts."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from institutions.models import Institution


class AccountViewTests(TestCase):
    """Garante telas de listagem, criacao, edicao e detalhe de contas."""

    def setUp(self):
        """Cria instituicoes base para os cenarios."""

        self.inter = Institution.objects.create(name="Inter", code="077")
        self.nomad = Institution.objects.create(name="Nomad", code="999")

    def test_account_list_page_returns_success(self):
        """Deve renderizar a lista de contas."""

        FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

        response = self.client.get(reverse("accounts:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/list.html")
        self.assertContains(response, "Conta corrente")
        self.assertContains(response, "Inter")
        self.assertContains(response, "Ativa")

    def test_account_list_page_shows_currency_grouping(self):
        """Deve exibir agrupamento por moeda calculado pelo selector."""

        FinancialAccount.objects.create(
            name="Conta BRL",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            currency=FinancialAccount.Currency.BRL,
            balance=Decimal("100.00"),
        )
        FinancialAccount.objects.create(
            name="Conta USD",
            institution=self.nomad,
            account_type=FinancialAccount.AccountType.GLOBAL,
            currency=FinancialAccount.Currency.USD,
            balance=Decimal("25.00"),
        )

        response = self.client.get(reverse("accounts:list"))

        self.assertEqual(response.context["account_summary"][0]["currency"], "BRL")
        self.assertEqual(
            response.context["account_summary"][0]["total_balance"],
            Decimal("100.00"),
        )
        self.assertEqual(response.context["account_summary"][1]["currency"], "USD")
        self.assertContains(response, "BRL")
        self.assertContains(response, "USD")

    def test_account_create_page_returns_form(self):
        """Deve renderizar formulario de criacao."""

        response = self.client.get(reverse("accounts:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/form.html")
        self.assertContains(response, "Nova conta")

    def test_post_create_account_creates_account(self):
        """Deve criar uma conta financeira."""

        response = self.client.post(
            reverse("accounts:create"),
            data={
                "name": "Conta corrente",
                "institution": self.inter.id,
                "account_type": FinancialAccount.AccountType.CHECKING,
                "currency": FinancialAccount.Currency.BRL,
                "balance": "1200.50",
                "is_active": "on",
            },
        )
        account = FinancialAccount.objects.get(name="Conta corrente")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("accounts:detail", kwargs={"account_id": account.id}),
        )
        self.assertEqual(account.balance, Decimal("1200.50"))
        self.assertTrue(account.is_active)

    def test_post_update_account_edits_account(self):
        """Deve editar uma conta financeira."""

        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

        response = self.client.post(
            reverse("accounts:update", kwargs={"account_id": account.id}),
            data={
                "name": "Reserva",
                "institution": self.inter.id,
                "account_type": FinancialAccount.AccountType.PIGGY_BANK,
                "currency": FinancialAccount.Currency.BRL,
                "balance": "1500.00",
            },
        )
        account.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(account.name, "Reserva")
        self.assertEqual(account.account_type, FinancialAccount.AccountType.PIGGY_BANK)
        self.assertEqual(account.balance, Decimal("1500.00"))
        self.assertFalse(account.is_active)

    def test_post_duplicate_name_in_same_institution_shows_form_error(self):
        """Deve validar nome unico por instituicao."""

        FinancialAccount.objects.create(
            name="Conta principal",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
        )

        response = self.client.post(
            reverse("accounts:create"),
            data={
                "name": "conta principal",
                "institution": self.inter.id,
                "account_type": FinancialAccount.AccountType.SAVINGS,
                "currency": FinancialAccount.Currency.BRL,
                "balance": "0.00",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/form.html")
        self.assertContains(
            response,
            "Já existe uma conta com este nome nesta instituição.",
        )
        self.assertEqual(FinancialAccount.objects.count(), 1)

    def test_account_detail_page_returns_success(self):
        """Deve renderizar detalhe de uma conta."""

        account = FinancialAccount.objects.create(
            name="Investimentos",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.INVESTMENT,
            balance=Decimal("5000.00"),
        )

        response = self.client.get(
            reverse("accounts:detail", kwargs={"account_id": account.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/detail.html")
        self.assertContains(response, "Investimentos")
