"""Tests dos selectors do app installments."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from installments.models import InstallmentPlan
from installments.selectors import (
    get_active_installment_plans,
    get_installment_plan_detail,
    get_installments_by_card,
    get_installments_ending_soon,
)
from installments.services import create_installment_plan
from institutions.models import Institution


class InstallmentSelectorTests(TestCase):
    """Garante consultas de parcelamentos."""

    def setUp(self):
        """Cria dados base para selectors."""

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
        self.other_card = Card.objects.create(
            name="Inter Platinum",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("8000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )
        self.category = Category.objects.create(name="Eletronicos")

    def test_get_active_installment_plans_returns_only_active(self):
        """Deve retornar apenas parcelamentos ativos."""

        active_plan = self._create_plan(description="Notebook", card=self.card)
        canceled_plan = self._create_plan(description="Celular", card=self.card)
        canceled_plan.status = InstallmentPlan.Status.CANCELED
        canceled_plan.save(update_fields=["status", "updated_at"])

        plans = list(get_active_installment_plans())

        self.assertEqual(plans, [active_plan])

    def test_get_installment_plan_detail_returns_plan(self):
        """Deve retornar detalhe do parcelamento."""

        plan = self._create_plan(description="Notebook", card=self.card)

        detail = get_installment_plan_detail(plan_id=plan.id)

        self.assertEqual(detail, plan)

    def test_get_installments_by_card_filters_card(self):
        """Deve filtrar parcelamentos por cartao."""

        plan = self._create_plan(description="Notebook", card=self.card)
        self._create_plan(description="Celular", card=self.other_card)

        plans = list(get_installments_by_card(card=self.card))

        self.assertEqual(plans, [plan])

    def test_get_installments_ending_soon_limits_results(self):
        """Deve limitar parcelamentos ativos proximos de terminar."""

        first_plan = self._create_plan(description="Curto", card=self.card, installments=2)
        self._create_plan(description="Longo", card=self.card, installments=10)

        plans = list(get_installments_ending_soon(limit=1))

        self.assertEqual(plans, [first_plan])

    def _create_plan(self, *, description, card, installments=3):
        """Cria parcelamento para testes."""

        return create_installment_plan(
            description=description,
            total_amount=Decimal("300.00"),
            total_installments=installments,
            first_installment_date=date(2026, 5, 8),
            card=card,
            category=self.category,
        )
