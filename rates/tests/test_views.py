"""Tests das views do app rates."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from institutions.models import Institution
from rates.models import AccountYieldConfig, ReferenceRate


class RateViewTests(TestCase):
    """Garante telas de taxas e simulacoes de rendimento."""

    def setUp(self):
        """Cria conta base para os formularios de rendimento."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Porquinho",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.PIGGY_BANK,
            balance=Decimal("1000.00"),
        )

    def test_rates_page_returns_success(self):
        """Deve renderizar a pagina principal de rendimentos."""

        response = self.client.get(reverse("rates:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rates/list.html")
        self.assertContains(response, "Rendimentos")

    def test_reference_rate_create_page_returns_form(self):
        """Deve renderizar formulario de cadastro manual do CDI."""

        response = self.client.get(reverse("rates:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rates/rate_form.html")
        self.assertContains(response, "Cadastrar CDI")

    def test_post_reference_rate_create_creates_cdi_and_redirects(self):
        """Deve cadastrar CDI e redirecionar para a lista."""

        response = self.client.post(
            reverse("rates:create"),
            data={
                "date": "2026-05-01",
                "value": "0.12000000",
                "notes": "Cadastro manual",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("rates:list"))
        self.assertTrue(
            ReferenceRate.objects.filter(
                date=date(2026, 5, 1),
                value=Decimal("0.12000000"),
            ).exists()
        )

    def test_post_reference_rate_create_invalid_shows_error(self):
        """Deve mostrar erro quando CDI informado for invalido."""

        response = self.client.post(
            reverse("rates:create"),
            data={
                "date": "2026-05-01",
                "value": "0",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rates/rate_form.html")
        self.assertContains(response, "Valor da taxa deve ser maior que zero.")
        self.assertEqual(ReferenceRate.objects.count(), 0)

    def test_yield_config_create_page_creates_config(self):
        """Deve criar configuracao de rendimento para conta."""

        response = self.client.post(
            reverse("rates:yield-config-create"),
            data={
                "account": self.account.id,
                "yield_type": AccountYieldConfig.YieldType.CDI_PERCENTAGE,
                "cdi_percentage": "100.0000",
                "is_active": "on",
            },
        )

        config = AccountYieldConfig.objects.get(account=self.account)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("rates:yield-config-edit", kwargs={"config_id": config.id}),
        )
        self.assertEqual(config.cdi_percentage, Decimal("100.0000"))

    def test_yield_config_update_page_updates_percentage(self):
        """Deve editar percentual do CDI em configuracao existente."""

        config = AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        response = self.client.post(
            reverse("rates:yield-config-edit", kwargs={"config_id": config.id}),
            data={
                "account": self.account.id,
                "yield_type": AccountYieldConfig.YieldType.CDI_PERCENTAGE,
                "cdi_percentage": "110.0000",
                "is_active": "on",
            },
        )

        config.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(config.cdi_percentage, Decimal("110.0000"))

    def test_yield_simulation_page_displays_estimate(self):
        """Deve exibir resultado de simulacao por conta configurada."""

        ReferenceRate.objects.create(
            rate_type=ReferenceRate.RateType.CDI,
            date=date(2026, 5, 1),
            value=Decimal("0.12000000"),
            periodicity=ReferenceRate.Periodicity.ANNUAL,
        )
        AccountYieldConfig.objects.create(
            account=self.account,
            yield_type=AccountYieldConfig.YieldType.CDI_PERCENTAGE,
            cdi_percentage=Decimal("100.0000"),
        )

        response = self.client.post(
            reverse("rates:simulate"),
            data={
                "account": self.account.id,
                "amount": "1000.00",
                "months": "12",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rates/simulation.html")
        self.assertEqual(response.context["estimate"]["final_amount"], Decimal("1120.00"))
        self.assertContains(response, "Valor final estimado")

    def test_sidebar_contains_rates_link(self):
        """Deve mostrar link de rendimentos no menu lateral."""

        response = self.client.get(reverse("rates:list"))

        self.assertContains(response, "Rendimentos")
        self.assertContains(response, 'href="/rates/"')
