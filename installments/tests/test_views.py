"""Tests das views do app installments."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from installments.models import InstallmentPlan
from installments.services import create_installment_plan
from institutions.models import Institution
from transactions.models import Transaction


class InstallmentViewTests(TestCase):
    """Garante telas de listagem, criacao e detalhe de parcelamentos."""

    def setUp(self):
        """Cria dados base para views."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.payment_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )
        self.category = Category.objects.create(name="Eletronicos")

    def test_installment_list_page_returns_success(self):
        """Deve renderizar a lista de parcelamentos."""

        create_installment_plan(
            description="Notebook",
            total_amount=Decimal("1000.00"),
            total_installments=10,
            first_installment_date=date(2026, 5, 8),
            card=self.card,
            category=self.category,
        )

        response = self.client.get(reverse("installments:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installments/list.html")
        self.assertContains(response, "Notebook")
        self.assertContains(response, "Inter Gold")

    def test_installment_create_page_returns_form(self):
        """Deve renderizar formulario de criacao."""

        response = self.client.get(reverse("installments:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installments/form.html")
        self.assertContains(response, "Novo parcelamento")

    def test_post_create_installment_plan_creates_transactions(self):
        """Deve criar parcelamento via POST e gerar parcelas."""

        response = self.client.post(
            reverse("installments:create"),
            data={
                "description": "Notebook",
                "total_amount": "1000.00",
                "total_installments": "10",
                "first_installment_date": "2026-05-08",
                "card": self.card.id,
                "category": self.category.id,
            },
        )
        plan = InstallmentPlan.objects.get(description="Notebook")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("installments:detail", kwargs={"plan_id": plan.id}),
        )
        self.assertEqual(plan.transactions.count(), 10)

    def test_installment_detail_page_returns_success(self):
        """Deve renderizar detalhe do parcelamento."""

        plan = create_installment_plan(
            description="Notebook",
            total_amount=Decimal("1000.00"),
            total_installments=10,
            first_installment_date=date(2026, 5, 8),
            card=self.card,
            category=self.category,
        )

        response = self.client.get(
            reverse("installments:detail", kwargs={"plan_id": plan.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installments/detail.html")
        self.assertContains(response, "Notebook")
        self.assertContains(response, "1/10")

    def test_get_cancel_installment_plan_shows_confirmation(self):
        """Deve mostrar tela de confirmacao no GET."""

        plan = create_installment_plan(
            description="Notebook",
            total_amount=Decimal("1000.00"),
            total_installments=10,
            first_installment_date=date(2026, 5, 8),
            card=self.card,
            category=self.category,
        )

        response = self.client.get(
            reverse("installments:cancel", kwargs={"plan_id": plan.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installments/confirm_cancellation.html")
        self.assertContains(response, "Confirmar Cancelamento")
        self.assertContains(response, "10/10")  # Todas estao pendentes

    def test_post_cancel_installment_plan_updates_status_and_transactions(self):
        """Deve cancelar parcelamento e suas parcelas pendentes."""

        plan = create_installment_plan(
            description="Notebook",
            total_amount=Decimal("1000.00"),
            total_installments=10,
            first_installment_date=date(2026, 5, 8),
            card=self.card,
            category=self.category,
        )

        response = self.client.post(
            reverse("installments:cancel", kwargs={"plan_id": plan.id}),
            follow=True
        )
        plan.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("installments:detail", kwargs={"plan_id": plan.id}))
        self.assertEqual(plan.status, InstallmentPlan.Status.CANCELED)
        
        # Todas as parcelas eram pendentes, entao todas devem ser canceladas
        self.assertEqual(
            Transaction.objects.filter(
                installment_plan=plan, 
                status=Transaction.PaymentStatus.CANCELED
            ).count(),
            10,
        )
        
        messages = list(response.context["messages"])
        self.assertEqual(str(messages[0]), "Parcelamento cancelado com sucesso.")
