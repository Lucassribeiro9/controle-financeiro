"""Testes de formatação pt-BR."""

from datetime import date
from datetime import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.forms import AnnualRateField
from core.forms import BRDateField
from core.forms import BRDecimalField
from core.templatetags.money import annual_rate
from core.templatetags.money import currency
from core.templatetags.money import date_br
from core.templatetags.money import month_name
from core.templatetags.money import percentage
from core.templatetags.money import status_badge_class
from core.templatetags.money import active_badge_class


class FormattingFilterTests(SimpleTestCase):
    """Garante formatação de moeda, data, percentual e taxa."""

    def test_currency_formats_brl_usd_and_fallback(self):
        self.assertEqual(currency(Decimal("1234.56"), "BRL"), "R$ 1.234,56")
        self.assertEqual(currency(Decimal("1234.56"), "USD"), "US$ 1.234,56")
        self.assertEqual(currency(Decimal("1234.56"), "EUR"), "EUR 1.234,56")

    def test_date_br_formats_date_and_datetime(self):
        self.assertEqual(date_br(date(2026, 5, 10)), "10/05/2026")
        self.assertEqual(
            date_br(datetime(2026, 5, 10, 15, 30)),
            "10/05/2026 15:30",
        )

    def test_month_name_formats_month_number(self):
        self.assertEqual(month_name(5), "Maio")
        self.assertEqual(month_name("12"), "Dezembro")
        self.assertEqual(month_name("sem mes"), "sem mes")

    def test_percentage_and_annual_rate_use_pt_br_decimal_separator(self):
        self.assertEqual(percentage(Decimal("100")), "100,00%")
        self.assertEqual(annual_rate(Decimal("0.11")), "11,00% a.a.")

    def test_status_badge_class_maps_common_operational_states(self):
        self.assertEqual(status_badge_class("paid"), "badge badge-success")
        self.assertEqual(status_badge_class("pending"), "badge badge-warning")
        self.assertEqual(status_badge_class("forecasted"), "badge badge-info")
        self.assertEqual(status_badge_class("ignored"), "badge badge-neutral")
        self.assertEqual(active_badge_class(True), "badge badge-success")
        self.assertEqual(active_badge_class(False), "badge badge-neutral")


class FormattingFieldTests(SimpleTestCase):
    """Garante normalização dos campos de entrada pt-BR."""

    def test_decimal_field_accepts_pt_br_and_iso_values(self):
        field = BRDecimalField(max_digits=14, decimal_places=2)

        self.assertEqual(field.clean("1.234,56"), Decimal("1234.56"))
        self.assertEqual(field.clean("1234.56"), Decimal("1234.56"))

    def test_date_field_accepts_pt_br_and_iso_values(self):
        field = BRDateField()

        self.assertEqual(field.clean("10/05/2026"), date(2026, 5, 10))
        self.assertEqual(field.clean("2026-05-10"), date(2026, 5, 10))

    def test_annual_rate_field_accepts_percentage_or_decimal(self):
        field = AnnualRateField(max_digits=18, decimal_places=8)

        self.assertEqual(field.clean("11,00"), Decimal("0.11"))
        self.assertEqual(field.clean("0,11"), Decimal("0.11"))
