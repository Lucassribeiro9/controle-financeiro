"""Tests dos forms do app categories."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from categories.forms import GoalForCategoryForm


class GoalForCategoryFormTests(SimpleTestCase):
    """Garante entrada em formato BR, mes e ano do form de meta."""

    def test_accepts_br_amount_month_and_year(self):
        form = GoalForCategoryForm(
            data={"target_amount": "1.234,56", "month": "10", "year": "2026"}
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["target_amount"], Decimal("1234.56"))
        self.assertEqual(form.cleaned_data["month"], 10)
        self.assertEqual(form.cleaned_data["year"], 2026)

    def test_rejects_non_numeric_amount_as_field_error(self):
        form = GoalForCategoryForm(
            data={"target_amount": "abc", "month": "10", "year": "2026"}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_amount", form.errors)

    def test_rejects_invalid_month_and_year(self):
        form = GoalForCategoryForm(
            data={"target_amount": "10,00", "month": "13", "year": "1999"}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("month", form.errors)
        self.assertIn("year", form.errors)

    def test_initial_period_is_current_local_month(self):
        with patch("categories.forms.timezone.localdate", return_value=date(2026, 10, 31)):
            form = GoalForCategoryForm()

        self.assertEqual(form.fields["month"].initial, 10)
        self.assertEqual(form.fields["year"].initial, 2026)

    def test_month_choices_use_portuguese_names(self):
        form = GoalForCategoryForm()

        choices = dict(form.fields["month"].choices)
        self.assertEqual(choices[1], "Janeiro")
        self.assertEqual(choices[12], "Dezembro")
