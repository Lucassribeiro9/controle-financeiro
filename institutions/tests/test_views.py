"""Tests das views do app institutions."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from cards.models import Card
from institutions.models import Institution


class InstitutionViewTests(TestCase):
    """Garante telas de listagem, criacao e edicao de instituicoes."""

    def test_institution_list_page_returns_success(self):
        """Deve renderizar a lista de instituicoes."""

        Institution.objects.create(name="Inter", code="077")

        response = self.client.get(reverse("institutions:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutions/list.html")
        self.assertContains(response, "Inter")
        self.assertContains(response, "077")
        self.assertContains(response, "Ativa")

    def test_institution_list_page_shows_accounts_and_cards_count(self):
        """Deve exibir quantidade de contas e cartoes vinculados."""

        institution = Institution.objects.create(name="Inter", code="077")
        FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        Card.objects.create(
            name="Cartao pre-pago",
            institution=institution,
            card_type=Card.CardType.PREPAID,
        )

        response = self.client.get(reverse("institutions:list"))
        institution_summary = response.context["institutions"][0]

        self.assertEqual(institution_summary.accounts_count, 1)
        self.assertEqual(institution_summary.cards_count, 1)

    def test_institution_create_page_returns_form(self):
        """Deve renderizar formulario de criacao."""

        response = self.client.get(reverse("institutions:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutions/form.html")
        self.assertContains(response, "Nova instituicao")

    def test_post_create_institution(self):
        """Deve criar instituicao financeira."""

        response = self.client.post(
            reverse("institutions:create"),
            data={
                "name": "Itaú",
                "official_name": "Banco Itau S.A.",
                "code": "341",
                "is_active": "on",
            },
        )
        institution = Institution.objects.get(name="Itaú")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("institutions:list"))
        self.assertEqual(institution.official_name, "Banco Itau S.A.")
        self.assertEqual(institution.code, "341")
        self.assertTrue(institution.is_active)

    def test_post_create_institution_without_code(self):
        """Deve permitir criar mais de uma instituicao sem codigo."""

        Institution.objects.create(name="Carteira")

        response = self.client.post(
            reverse("institutions:create"),
            data={
                "name": "Dinheiro",
                "official_name": "",
                "code": "",
                "is_active": "on",
            },
        )
        institution = Institution.objects.get(name="Dinheiro")

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(institution.code)

    def test_post_update_institution_edits_institution(self):
        """Deve editar uma instituicao financeira."""

        institution = Institution.objects.create(name="Inter", code="077")

        response = self.client.post(
            reverse(
                "institutions:update",
                kwargs={"institution_id": institution.id},
            ),
            data={
                "name": "Inter Empresas",
                "official_name": "Banco Inter S.A.",
                "code": "077",
            },
        )
        institution.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(institution.name, "Inter Empresas")
        self.assertEqual(institution.official_name, "Banco Inter S.A.")
        self.assertFalse(institution.is_active)

    def test_post_duplicate_name_shows_form_error(self):
        """Deve validar nome unico."""

        Institution.objects.create(name="Nubank", code="260")

        response = self.client.post(
            reverse("institutions:create"),
            data={
                "name": "nubank",
                "official_name": "",
                "code": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutions/form.html")
        self.assertContains(response, "Ja existe uma instituicao com este nome.")
        self.assertEqual(Institution.objects.count(), 1)

    def test_post_duplicate_code_when_informed_shows_form_error(self):
        """Deve validar codigo unico quando informado."""

        Institution.objects.create(name="Inter", code="077")

        response = self.client.post(
            reverse("institutions:create"),
            data={
                "name": "Outro banco",
                "official_name": "",
                "code": "077",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutions/form.html")
        self.assertContains(response, "Ja existe uma instituicao com este codigo.")
        self.assertEqual(Institution.objects.count(), 1)
