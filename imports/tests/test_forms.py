"""Tests do form de filtros da revisao de importacoes."""

from datetime import date

from django.http import QueryDict
from django.test import SimpleTestCase

from core.forms import BRDateInput
from imports.forms import ImportReviewFilterForm


def _form(query=""):
    form = ImportReviewFilterForm(QueryDict(query))
    form.is_valid()
    return form


class ImportReviewFilterFormTests(SimpleTestCase):
    def test_date_fields_use_brdateinput(self):
        form = ImportReviewFilterForm()

        self.assertIsInstance(form.fields["start_date"].widget, BRDateInput)
        self.assertIsInstance(form.fields["end_date"].widget, BRDateInput)
        self.assertEqual(form.fields["start_date"].widget.attrs["placeholder"], "dd/mm/aaaa")

    def test_parses_br_and_iso_into_iso_filters(self):
        form = _form("start_date=01/05/2026&end_date=2026-05-31")

        self.assertEqual(
            form.date_filters(),
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )
        self.assertEqual(form.cleaned_data["start_date"], date(2026, 5, 1))

    def test_iso_value_is_rendered_back_as_br(self):
        form = _form("start_date=2026-05-01")

        self.assertIn('value="01/05/2026"', str(form["start_date"]))

    def test_invalid_date_is_ignored_and_reports_error(self):
        form = _form("start_date=31/02/2026&end_date=2026-13-45")

        self.assertEqual(form.date_filters(), {})
        self.assertIn("start_date", form.errors)
        self.assertIn("end_date", form.errors)

    def test_merge_replaces_raw_dates_with_clean_ones(self):
        form = _form("start_date=01/05/2026&end_date=lixo")

        merged = form.merge_into({"tab": "pendentes", "start_date": "01/05/2026", "end_date": "lixo"})

        self.assertEqual(merged, {"tab": "pendentes", "start_date": "2026-05-01"})

    def test_active_count_counts_the_seven_collapsible_filters(self):
        self.assertEqual(_form().active_count, 0)
        self.assertEqual(_form("q=abc&tab=tratadas&page=2").active_count, 0)
        query = (
            "source_file_name=a.csv&source_type=csv&account_id=1&category_id=2"
            "&transaction_type=expense&start_date=01/05/2026&end_date=31/05/2026"
        )
        self.assertEqual(_form(query).active_count, 7)

    def test_invalid_date_does_not_count_as_active(self):
        self.assertEqual(_form("start_date=xx&account_id=3").active_count, 1)
