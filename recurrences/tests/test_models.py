"""Tests dos models do app recurrences."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from institutions.models import Institution
from recurrences.models import Recurrence


class RecurrenceModelTests(TestCase):
    """Garante as regras principais do model Recurrence."""

    def setUp(self):
        """Cria dados base para os cenarios de recorrencia."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.card = Card.objects.create(
            name="Nubank",
            institution=self.institution,
            card_type=Card.CardType.PREPAID,
        )

    def test_create_fixed_bill_recurrence_with_account(self):
        """Deve criar recorrencia de despesa fixa quando ha conta vinculada."""

        recurrence = Recurrence(
            name="Internet",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
            requires_confirmation=True,
        )
        recurrence.full_clean()
        recurrence.save()

        self.assertEqual(recurrence.name, "Internet")
        self.assertEqual(recurrence.account, self.account)
        self.assertTrue(recurrence.is_active)

    def test_expected_day_must_be_between_one_and_thirty_one(self):
        """Nao deve validar recorrencia com dia esperado fora do intervalo."""

        recurrence = Recurrence(
            name="Internet",
            expected_day=32,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
        )

        with self.assertRaises(ValidationError):
            recurrence.full_clean()

    def test_expected_amount_must_be_positive(self):
        """Nao deve validar recorrencia com valor esperado zero ou negativo."""

        recurrence = Recurrence(
            name="Streaming",
            expected_day=5,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            expected_amount=Decimal("0.00"),
            card=self.card,
        )

        with self.assertRaises(ValidationError):
            recurrence.full_clean()

    def test_fixed_bill_requires_account(self):
        """Recorrencia de despesa fixa deve exigir conta vinculada."""

        recurrence = Recurrence(
            name="Condominio",
            expected_day=7,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("500.00"),
        )

        with self.assertRaises(ValidationError):
            recurrence.full_clean()

    def test_subscription_requires_card(self):
        """Recorrencia de assinatura deve exigir cartao vinculado."""

        recurrence = Recurrence(
            name="Musica",
            expected_day=15,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            expected_amount=Decimal("19.90"),
        )

        with self.assertRaises(ValidationError):
            recurrence.full_clean()

    def test_str_returns_name_type_frequency_and_amount(self):
        """O __str__ deve retornar nome, tipo, frequencia e valor esperado."""

        recurrence = Recurrence(
            name="Internet",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
        )

        expected = "Internet (Despesa fixa, Mensal) - R$ 120.00"
        self.assertEqual(str(recurrence), expected)
