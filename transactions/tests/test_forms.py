"""Tests dos forms do app transactions."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import FinancialAccount
from cards.models import Card
from categories.models import Category
from institutions.models import Institution
from transactions.forms import TransactionForm, TransferForm
from transactions.models import Transaction


class TransactionFormTests(TestCase):
    """Garante o contrato dinamico do formulario de lancamentos."""

    def setUp(self):
        """Cria dados base para os cenarios do form."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.destination_account = FinancialAccount.objects.create(
            name="Conta reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )
        self.category = Category.objects.create(name="Alimentacao")
        self.credit_card = Card.objects.create(
            name="Inter Gold",
            institution=self.institution,
            card_type=Card.CardType.CREDIT,
            credit_limit=Decimal("5000.00"),
            statement_closing_day=20,
            statement_due_day=27,
            payment_account=self.account,
        )
        self.benefit_card = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("300.00"),
            balance=Decimal("300.00"),
        )

    def _data(self, **overrides):
        data = {
            "description": "Lancamento",
            "transaction_type": "expense",
            "source": f"account:{self.account.id}",
            "amount": "100,00",
            "status": Transaction.PaymentStatus.PENDING,
            "category": self.category.id,
            "date": "2026-05-08",
            "notes": "",
        }
        data.update(overrides)
        return data

    def _card(self, card_type, name=None):
        return Card.objects.create(
            name=name or f"Cartao {card_type}",
            institution=self.institution,
            card_type=card_type,
            balance=Decimal("100.00"),
        )

    def test_form_exposes_type_and_single_source_field(self):
        """O form pergunta o tipo e uma origem unica; sem forma de pagamento."""

        form = TransactionForm()

        self.assertIn("source", form.fields)
        self.assertNotIn("payment_method", form.fields)
        self.assertNotIn("account", form.fields)
        self.assertNotIn("card", form.fields)
        self.assertEqual(
            [value for value, _ in form.fields["transaction_type"].choices],
            ["income", "expense", "transfer"],
        )

    def test_source_choices_are_grouped_by_account_credit_and_balance(self):
        """Origem lista contas, cartoes de credito e cartoes de saldo."""

        transport = self._card(Card.CardType.TRANSPORT, "VT")
        prepaid = self._card(Card.CardType.PREPAID, "Pre")

        groups = {
            label: [value for value, _ in options]
            for label, options in TransactionForm().fields["source"].choices
            if isinstance(options, (list, tuple))
        }

        self.assertEqual(
            groups["Contas"],
            [f"account:{self.account.id}", f"account:{self.destination_account.id}"],
        )
        self.assertEqual(groups["Cartões de crédito"], [f"card:{self.credit_card.id}"])
        self.assertEqual(
            sorted(groups["Cartões de saldo"]),
            sorted(
                [
                    f"card:{self.benefit_card.id}",
                    f"card:{transport.id}",
                    f"card:{prepaid.id}",
                ]
            ),
        )

    def test_expense_in_account_derives_debit_and_account(self):
        form = TransactionForm(data=self._data())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["payment_method"], "debit")
        self.assertEqual(
            form.cleaned_data["transaction_type"], Transaction.TransactionType.EXPENSE
        )
        self.assertEqual(form.cleaned_data["account"], self.account)
        self.assertIsNone(form.cleaned_data["card"])

    def test_income_in_account_derives_income(self):
        form = TransactionForm(data=self._data(transaction_type="income"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["transaction_type"], Transaction.TransactionType.INCOME
        )
        self.assertEqual(form.cleaned_data["account"], self.account)

    def test_income_rejects_cards_with_message_on_source(self):
        for card in (self.credit_card, self.benefit_card):
            with self.subTest(card=card.card_type):
                form = TransactionForm(
                    data=self._data(transaction_type="income", source=f"card:{card.id}")
                )

                self.assertFalse(form.is_valid())
                self.assertIn("source", form.errors)

    def test_expense_on_credit_card_derives_card_purchase(self):
        form = TransactionForm(data=self._data(source=f"card:{self.credit_card.id}"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["payment_method"], "credit")
        self.assertEqual(
            form.cleaned_data["transaction_type"],
            Transaction.TransactionType.CARD_PURCHASE,
        )
        self.assertEqual(form.cleaned_data["card"], self.credit_card)
        self.assertIsNone(form.cleaned_data["account"])

    def test_expense_on_any_balance_card_derives_benefit_purchase(self):
        for card_type in (
            Card.CardType.BENEFIT,
            Card.CardType.PREPAID,
            Card.CardType.TRANSPORT,
        ):
            with self.subTest(card_type=card_type):
                card = (
                    self.benefit_card
                    if card_type == Card.CardType.BENEFIT
                    else self._card(card_type)
                )
                form = TransactionForm(data=self._data(source=f"card:{card.id}"))

                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["payment_method"], "benefit")
                self.assertEqual(
                    form.cleaned_data["transaction_type"],
                    Transaction.TransactionType.BENEFIT_PURCHASE,
                )
                self.assertEqual(form.cleaned_data["card"], card)

    def test_installments_accepted_only_for_credit_card(self):
        ok = TransactionForm(
            data=self._data(
                source=f"card:{self.credit_card.id}", total_installments="10"
            )
        )
        in_account = TransactionForm(data=self._data(total_installments="3"))
        in_balance_card = TransactionForm(
            data=self._data(source=f"card:{self.benefit_card.id}", total_installments="3")
        )

        self.assertTrue(ok.is_valid(), ok.errors)
        for form in (in_account, in_balance_card):
            self.assertFalse(form.is_valid())
            self.assertIn("total_installments", form.errors)

    def test_credit_rejects_single_installment(self):
        form = TransactionForm(
            data=self._data(
                source=f"card:{self.credit_card.id}", total_installments="1"
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("total_installments", form.errors)

    def test_missing_source_is_rejected_for_income_and_expense(self):
        for kind in ("income", "expense"):
            with self.subTest(kind=kind):
                form = TransactionForm(data=self._data(transaction_type=kind, source=""))

                self.assertFalse(form.is_valid())
                self.assertIn("source", form.errors)

    def test_unknown_or_malformed_source_is_rejected(self):
        for value in ("account:99999", "card:99999", "abc", "card:", f"{self.account.id}"):
            with self.subTest(value=value):
                form = TransactionForm(data=self._data(source=value))

                self.assertFalse(form.is_valid())
                self.assertIn("source", form.errors)

    def test_inactive_origins_are_not_offered(self):
        self.account.is_active = False
        self.account.save()

        form = TransactionForm(data=self._data())

        self.assertFalse(form.is_valid())
        self.assertIn("source", form.errors)

    def test_transfer_requires_different_accounts(self):
        form = TransactionForm(
            data=self._data(
                transaction_type="transfer",
                source="",
                from_account=self.account.id,
                destination_account=self.account.id,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("destination_account", form.errors)

    def test_transfer_is_valid_with_two_accounts_and_ignores_source(self):
        form = TransactionForm(
            data=self._data(
                transaction_type="transfer",
                source="",
                from_account=self.account.id,
                destination_account=self.destination_account.id,
            )
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["payment_method"], "transfer")

    def test_transfer_is_rejected_when_not_allowed(self):
        form = TransactionForm(
            data=self._data(
                transaction_type="transfer",
                source="",
                from_account=self.account.id,
                destination_account=self.destination_account.id,
            ),
            allow_transfer=False,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("transaction_type", form.errors)
        self.assertNotIn(
            "transfer",
            [value for value, _ in TransactionForm(allow_transfer=False).fields["transaction_type"].choices],
        )

    def test_saved_inactive_origin_stays_available_when_editing(self):
        transaction = Transaction.objects.create(
            description="Antigo",
            amount=Decimal("10.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account,
            date=date(2026, 5, 8),
            status=Transaction.PaymentStatus.PENDING,
        )
        self.account.is_active = False
        self.account.save()

        form = TransactionForm(
            self._data(), allow_transfer=False, transaction=transaction
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_from_transaction_initial_for_each_saved_origin(self):
        income = Transaction.objects.create(
            description="Salario", amount=Decimal("10.00"),
            transaction_type=Transaction.TransactionType.INCOME,
            account=self.account, date=date(2026, 5, 8),
        )
        expense = Transaction.objects.create(
            description="Mercado", amount=Decimal("10.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            account=self.account, date=date(2026, 5, 8),
        )
        credit = Transaction.objects.create(
            description="Notebook", amount=Decimal("10.00"),
            transaction_type=Transaction.TransactionType.CARD_PURCHASE,
            card=self.credit_card, date=date(2026, 5, 8),
        )
        transport = self._card(Card.CardType.TRANSPORT)
        balance = Transaction.objects.create(
            description="Passagem", amount=Decimal("10.00"),
            transaction_type=Transaction.TransactionType.BENEFIT_PURCHASE,
            card=transport, date=date(2026, 5, 8),
        )

        expected = [
            (income, "income", f"account:{self.account.id}"),
            (expense, "expense", f"account:{self.account.id}"),
            (credit, "expense", f"card:{self.credit_card.id}"),
            (balance, "expense", f"card:{transport.id}"),
        ]
        for transaction, kind, source in expected:
            with self.subTest(transaction=transaction.description):
                form = TransactionForm.from_transaction(transaction)

                self.assertEqual(form.initial["transaction_type"], kind)
                self.assertEqual(form.initial["source"], source)


class TransferFormTests(TestCase):
    """Mantem o contrato do formulario de transferencias."""

    def setUp(self):
        """Cria contas base para o form."""

        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.destination_account = FinancialAccount.objects.create(
            name="Conta reserva",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.SAVINGS,
            balance=Decimal("500.00"),
        )

    def test_transfer_form_requires_different_accounts(self):
        """TransferForm segue exigindo contas distintas."""

        form = TransferForm(
            data={
                "description": "Aporte",
                "amount": "100.00",
                "from_account": self.account.id,
                "destination_account": self.account.id,
                "date": "2026-05-08",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("destination_account", form.errors)


class AdjustmentTypeFormTests(TestCase):
    """Tipos de ajuste nao sao oferecidos nem aceitos no form de lancamento."""

    def test_adjustment_types_are_not_choices(self):
        values = [value for value, _ in TransactionForm().fields["transaction_type"].choices]

        self.assertNotIn(Transaction.TransactionType.ADJUSTMENT_IN, values)
        self.assertNotIn(Transaction.TransactionType.ADJUSTMENT_OUT, values)

    def test_post_with_adjustment_type_is_rejected(self):
        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta", institution=institution, balance=Decimal("10.00")
        )

        for kind in (
            Transaction.TransactionType.ADJUSTMENT_IN,
            Transaction.TransactionType.ADJUSTMENT_OUT,
        ):
            form = TransactionForm(
                data={
                    "description": "Ajuste",
                    "amount": "10.00",
                    "transaction_type": kind,
                    "source": f"account:{account.id}",
                    "status": Transaction.PaymentStatus.PAID,
                    "date": "2026-05-08",
                }
            )

            self.assertFalse(form.is_valid())
            self.assertIn("transaction_type", form.errors)
