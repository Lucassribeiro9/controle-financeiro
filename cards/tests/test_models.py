"""Tests dos models do app cards."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from institutions.models import Institution


class CardModelTests(TestCase):
    """Garante as regras principais do model Card."""

    def setUp(self):
        """Cria dados base para cenarios de cartao."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.payment_account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )

    def test_create_credit_card_with_required_fields(self):
        """Deve criar cartao de credito com limite, fechamento, vencimento e conta."""

        card = Card(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.payment_account,
        )
        card.full_clean()
        card.save()

        self.assertEqual(card.card_type, Card.CardType.CREDIT)
        self.assertEqual(card.credit_limit, Decimal("5000.00"))

    def test_credit_card_requires_payment_configuration(self):
        """Nao deve validar cartao de credito sem configuracoes obrigatorias."""

        card = Card(
            name="Cartao incompleto",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("3000.00"),
        )

        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_create_benefit_card_with_estimated_balance(self):
        """Deve criar cartao de beneficio com saldo estimado."""

        card = Card(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("850.00"),
        )
        card.full_clean()
        card.save()

        self.assertEqual(card.estimated_balance, Decimal("850.00"))

    def test_benefit_card_requires_estimated_balance(self):
        """Nao deve validar cartao de beneficio sem saldo estimado."""

        card = Card(
            name="Caju VR",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
        )

        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_card_name_must_be_unique_per_institution(self):
        """Nao deve permitir mesmo nome de cartao na mesma instituicao."""

        Card.objects.create(
            name="Nubank",
            institution=self.institution,
            card_type=Card.CardType.PREPAID,
        )

        with self.assertRaises(IntegrityError):
            Card.objects.create(
                name="Nubank",
                institution=self.institution,
                card_type=Card.CardType.TRANSPORT,
            )
