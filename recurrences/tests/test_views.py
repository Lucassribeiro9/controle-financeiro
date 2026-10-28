"""Tests das views do app recurrences."""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal

from core.testing import AuthenticatedTestCase
from django.utils import timezone
from django.urls import reverse

from accounts.models import FinancialAccount
from cards.models import Card
from institutions.models import Institution
from recurrences.models import Recurrence
from transactions.models import Transaction


class RecurrenceViewsTests(AuthenticatedTestCase):
    """Garante fluxo de confirmar, ignorar e ajustar previsoes."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=self.institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        self.recurrence = Recurrence.objects.create(
            name="Internet residencial",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.FIXED_BILL,
            expected_amount=Decimal("120.00"),
            account=self.account,
            requires_confirmation=True,
            is_active=True,
        )
        self.forecast = Transaction.objects.create(
            description="[REC] Internet residencial",
            amount=Decimal("120.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 6, 10),
            recurrence=self.recurrence,
        )

    def test_monthly_forecasts_returns_month_items(self):
        response = self.client.get(
            reverse("recurrences:monthly-forecasts", kwargs={"year": 2026, "month": 6})
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["id"], self.forecast.id)

    def test_forecasts_page_lists_month_items(self):
        response = self.client.get(
            reverse("recurrences:forecasts-page", kwargs={"year": 2026, "month": 6})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recurrences/forecasts.html")
        self.assertContains(response, "Internet residencial")
        self.assertContains(response, "Confirmar")
        self.assertContains(response, 'class="badge badge-info"', html=False)

    def test_forecasts_filter_page_uses_query_period(self):
        response = self.client.get(
            reverse("recurrences:forecasts-filter-page"),
            data={"year": 2026, "month": 6},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], 2026)
        self.assertEqual(response.context["month"], 6)
        self.assertTemplateUsed(response, "recurrences/forecasts.html")
        self.assertContains(response, "Internet residencial")

    def test_forecasts_filter_page_uses_current_period_by_default(self):
        today = timezone.localdate()

        response = self.client.get(reverse("recurrences:forecasts-filter-page"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], today.year)
        self.assertEqual(response.context["month"], today.month)

    def _url(self, name, forecast=None):
        forecast = forecast or self.forecast
        return reverse(f"recurrences:{name}-forecast", kwargs={"transaction_id": forecast.id})

    @property
    def month_url(self):
        return reverse("recurrences:forecasts-page", kwargs={"year": 2026, "month": 6})

    def _post(self, name, forecast=None, **data):
        """Posta, segue o redirect (consumindo as messages) e valida o destino."""

        response = self.client.post(self._url(name, forecast), data=data, follow=True)
        self.assertEqual(response.redirect_chain, [(self.month_url, 302)])
        return response

    def _messages(self, response):
        return [(m.level_tag, str(m)) for m in response.context["messages"]]

    def test_confirm_forecast_sets_pending_and_expense(self):
        response = self._post("confirm")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(self.forecast.transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(
            self._messages(response), [("success", "Previsão confirmada com sucesso.")]
        )

    def test_confirm_forecast_response_is_not_json(self):
        response = self.client.post(self._url("confirm"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recurrences/forecasts.html")
        self.assertContains(response, "Previsão confirmada com sucesso.")

    def test_confirm_forecast_twice_is_noop(self):
        self._post("confirm")
        self.forecast.refresh_from_db()
        updated_at = self.forecast.updated_at

        response = self._post("confirm")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.updated_at, updated_at)
        self.assertEqual(self._messages(response), [("info", "Esta previsão já foi confirmada.")])

    def test_confirm_forecast_with_homonym_recurrences_uses_linked_recurrence(self):
        """Homonimas de tipos diferentes confirmam cada uma com o tipo correto."""

        income = Recurrence.objects.create(
            name=self.recurrence.name,
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.INCOME,
            expected_amount=Decimal("300.00"),
            account=self.account,
        )
        income_forecast = Transaction.objects.create(
            description=f"[REC] {income.name}",
            amount=Decimal("300.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            account=self.account,
            date=date(2026, 6, 10),
            recurrence=income,
        )

        for forecast in (self.forecast, income_forecast):
            response = self.client.post(self._url("confirm", forecast))
            self.assertEqual(response.status_code, 302)
            forecast.refresh_from_db()

        self.assertEqual(self.forecast.transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(income_forecast.transaction_type, Transaction.TransactionType.INCOME)

    def test_confirm_forecast_works_after_recurrence_rename(self):
        """Renomear a recorrencia nao deixa a previsao orfa."""

        self.recurrence.name = "Internet fibra"
        self.recurrence.save()

        response = self._post("confirm")

        self.assertEqual(self._messages(response)[0][0], "success")

    def test_confirm_forecast_without_recurrence_returns_404(self):
        """Previsao sem vinculo (ex.: anterior ao campo) responde 404 HTML."""

        self.forecast.recurrence = None
        self.forecast.save(update_fields=["recurrence"])

        response = self.client.post(self._url("confirm"))
        self.forecast.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response["Content-Type"], "application/json")
        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.FORECASTED)

    def test_actions_on_missing_id_return_html_404(self):
        for name in ("confirm", "ignore", "adjust"):
            with self.subTest(action=name):
                response = self.client.post(
                    reverse(f"recurrences:{name}-forecast", kwargs={"transaction_id": 999999})
                )
                self.assertEqual(response.status_code, 404)
                self.assertNotEqual(response["Content-Type"], "application/json")

    def test_actions_require_post(self):
        for name in ("confirm", "ignore", "adjust"):
            with self.subTest(action=name):
                self.assertEqual(self.client.get(self._url(name)).status_code, 405)

    def test_actions_redirect_anonymous_to_login(self):
        self.client.logout()
        for name in ("confirm", "ignore", "adjust"):
            with self.subTest(action=name):
                response = self.client.post(self._url(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response["Location"])
        self.forecast.refresh_from_db()
        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.FORECASTED)

    def test_ignore_forecast_sets_ignored_status(self):
        response = self._post("ignore")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.IGNORED)
        self.assertEqual(
            self._messages(response), [("success", "Previsão ignorada com sucesso.")]
        )

    def test_ignore_forecast_twice_is_noop(self):
        self._post("ignore")
        response = self._post("ignore")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.IGNORED)
        self.assertEqual(self._messages(response), [("info", "Esta previsão já foi ignorada.")])

    def test_ignore_confirmed_forecast_is_rejected(self):
        self._post("confirm")
        response = self._post("ignore")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.PENDING)
        self.assertEqual(self._messages(response)[0][0], "error")

    def test_adjust_forecast_updates_amount(self):
        response = self._post("adjust", amount="135,50")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.amount, Decimal("135.50"))
        self.assertIn("[REC_ADJUST]", self.forecast.notes)
        self.assertEqual(
            self._messages(response), [("success", "Previsão ajustada com sucesso.")]
        )

    def test_adjust_forecast_rejects_invalid_amounts_without_saving(self):
        cases = {
            "": "Informe o novo valor da previsão.",
            "abc": "Valor inválido. Use o formato 0,00.",
            "NaN": "Valor inválido. Use o formato 0,00.",
            "0": "O novo valor deve ser maior que zero.",
            "-5": "O novo valor deve ser maior que zero.",
        }
        for amount, expected in cases.items():
            with self.subTest(amount=amount):
                response = self._post("adjust", amount=amount)
                self.forecast.refresh_from_db()

                self.assertEqual(self._messages(response), [("error", expected)])
                self.assertEqual(self.forecast.amount, Decimal("120.00"))
                self.assertEqual(self.forecast.notes, "")

    def test_adjust_forecast_with_same_amount_is_noop(self):
        response = self._post("adjust", amount="120,00")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.notes, "")
        self.assertEqual(self._messages(response)[0][0], "info")

    def test_adjust_confirmed_forecast_is_rejected(self):
        self._post("confirm")
        response = self._post("adjust", amount="200,00")
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.amount, Decimal("120.00"))
        self.assertEqual(self._messages(response)[0][0], "error")

    def test_forecasts_page_shows_messages_after_redirect(self):
        response = self.client.post(
            self._url("adjust"), data={"amount": "0"}, follow=True
        )

        self.assertContains(response, "O novo valor deve ser maior que zero.")

    def test_adjust_forecast_full_clean_error_is_readable_and_not_saved(self):
        error = ValidationError({"amount": ["Valor invalido."]})

        with patch.object(Transaction, "full_clean", side_effect=error):
            response = self._post("adjust", amount="135,50")
        self.forecast.refresh_from_db()

        self.assertEqual(self._messages(response), [("error", "Valor invalido.")])
        self.assertEqual(self.forecast.amount, Decimal("120.00"))


class ConfirmSubscriptionOnCardViewTests(AuthenticatedTestCase):
    """Confirmar assinatura no cartao gera compra no cartao na fatura (#217)."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(
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
            payment_account=self.account,
        )
        self.recurrence = Recurrence.objects.create(
            name="Streaming",
            expected_day=10,
            frequency=Recurrence.Frequency.MONTHLY,
            recurrence_type=Recurrence.RecurrenceType.SUBSCRIPTION,
            expected_amount=Decimal("50.00"),
            card=self.card,
        )
        self.forecast = Transaction.objects.create(
            description="[REC] Streaming",
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.FORECAST,
            status=Transaction.PaymentStatus.FORECASTED,
            card=self.card,
            date=date(2026, 6, 10),
            recurrence=self.recurrence,
        )
        self.url = reverse(
            "recurrences:confirm-forecast", kwargs={"transaction_id": self.forecast.id}
        )

    def test_confirm_subscription_creates_card_purchase_in_statement(self):
        response = self.client.post(self.url, follow=True)
        self.forecast.refresh_from_db()

        self.assertEqual(
            self.forecast.transaction_type, Transaction.TransactionType.CARD_PURCHASE
        )
        self.assertIsNotNone(self.forecast.statement)
        self.assertEqual(self.forecast.statement.expected_amount, Decimal("50.00"))
        self.assertEqual(
            [(m.level_tag, str(m)) for m in response.context["messages"]],
            [("success", "Previsão confirmada com sucesso.")],
        )

    def test_confirm_twice_does_not_duplicate_statement_amount(self):
        self.client.post(self.url)
        self.client.post(self.url)
        self.forecast.refresh_from_db()

        self.assertEqual(self.forecast.statement.expected_amount, Decimal("50.00"))

    def test_confirm_with_balance_card_shows_error_and_keeps_forecast(self):
        benefit = Card.objects.create(
            name="Caju VA",
            institution=self.institution,
            card_type=Card.CardType.BENEFIT,
            estimated_balance=Decimal("100.00"),
            balance=Decimal("100.00"),
        )
        self.forecast.card = benefit
        self.forecast.save()
        self.recurrence.card = benefit
        self.recurrence.save()

        response = self.client.post(self.url, follow=True)
        self.forecast.refresh_from_db()

        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertEqual(self.forecast.transaction_type, Transaction.TransactionType.FORECAST)
        self.assertEqual(self.forecast.status, Transaction.PaymentStatus.FORECASTED)
        self.assertEqual(
            [m.level_tag for m in response.context["messages"]], ["error"]
        )
