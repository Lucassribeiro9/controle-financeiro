"""Tests das views do app accounts."""

from decimal import Decimal

from core.testing import AuthenticatedTestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from institutions.models import Institution
from transactions.models import Transaction


class AccountViewTests(AuthenticatedTestCase):
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
        self.assertContains(response, 'class="badge badge-success"', html=False)

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
        self.assertEqual(account.balance, Decimal("1000.00"))
        self.assertFalse(account.is_active)

    def test_update_page_shows_balance_read_only_with_adjust_link(self):
        """Edicao mostra o saldo sem campo editavel e linka o ajuste."""

        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.inter,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

        response = self.client.get(
            reverse("accounts:update", kwargs={"account_id": account.id})
        )

        self.assertNotIn("balance", response.context["form"].fields)
        self.assertContains(
            response,
            reverse("accounts:adjust_balance", kwargs={"account_id": account.id}),
        )

    def test_create_page_keeps_initial_balance_field(self):
        response = self.client.get(reverse("accounts:create"))

        self.assertIn("balance", response.context["form"].fields)

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


class AccountBalanceAdjustmentViewTests(AuthenticatedTestCase):
    """Garante a tela de ajuste de saldo e a edicao sem saldo (spec 013)."""

    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.url = reverse("accounts:adjust_balance", kwargs={"account_id": self.account.id})

    def test_get_renders_form_without_writing(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/adjust_balance.html")
        self.assertEqual(Transaction.objects.count(), 0)

    def test_post_adjusts_balance_and_redirects_with_message(self):
        response = self.client.post(self.url, data={"real_balance": "950,00", "notes": "Conferido"})

        self.assertRedirects(
            response, reverse("accounts:detail", kwargs={"account_id": self.account.id})
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("950.00"))
        adjustment = Transaction.objects.get()
        self.assertEqual(adjustment.transaction_type, Transaction.TransactionType.ADJUSTMENT_OUT)
        self.assertEqual(adjustment.notes, "Conferido")

    def test_post_shows_success_message_and_lists_adjustment_in_detail(self):
        response = self.client.post(self.url, data={"real_balance": "1100,00"}, follow=True)

        self.assertContains(response, "Saldo ajustado com sucesso.")
        self.assertContains(response, "Ajuste de saldo")
        self.assertContains(response, "Ajuste de entrada")

    def test_post_same_balance_warns_and_creates_nothing(self):
        response = self.client.post(self.url, data={"real_balance": "1000,00"}, follow=True)

        self.assertContains(response, "nada foi alterado")
        self.assertEqual(Transaction.objects.count(), 0)

    def test_post_twice_applies_once(self):
        self.client.post(self.url, data={"real_balance": "950,00"})
        self.client.post(self.url, data={"real_balance": "950,00"})

        self.assertEqual(Transaction.objects.count(), 1)

    def test_post_more_than_two_decimals_is_rejected(self):
        response = self.client.post(self.url, data={"real_balance": "950,005"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("real_balance", response.context["form"].errors)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_post_inactive_account_shows_error(self):
        self.account.is_active = False
        self.account.save()

        response = self.client.post(self.url, data={"real_balance": "900,00"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reative a conta para ajustar o saldo.")
        self.assertEqual(Transaction.objects.count(), 0)

    def test_unknown_account_returns_404(self):
        response = self.client.get(reverse("accounts:adjust_balance", kwargs={"account_id": 9999}))

        self.assertEqual(response.status_code, 404)

    def test_detail_links_to_adjust_balance(self):
        response = self.client.get(
            reverse("accounts:detail", kwargs={"account_id": self.account.id})
        )

        self.assertContains(response, self.url)
