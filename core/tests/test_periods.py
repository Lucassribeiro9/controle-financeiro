"""Tests do helper de periodo da URL e das telas que o usam (#225)."""

from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from core.periods import MAX_YEAR, MIN_YEAR, get_period_from_request
from core.testing import AuthenticatedTestCase
from goals.models import Goal

FIXED_TODAY = date(2026, 5, 17)


def _period(**params):
    request = RequestFactory().get("/", params)
    with patch("core.periods.timezone.localdate", return_value=FIXED_TODAY):
        return get_period_from_request(request)


class GetPeriodFromRequestTests(SimpleTestCase):
    def test_empty_uses_current_month(self):
        self.assertEqual(_period(), (2026, 5))

    def test_blank_values_are_absent(self):
        self.assertEqual(_period(year="", month=""), (2026, 5))
        self.assertEqual(_period(year="   ", month="  "), (2026, 5))

    def test_valid_values(self):
        self.assertEqual(_period(year="2025", month="3"), (2025, 3))

    def test_values_with_spaces_are_accepted(self):
        self.assertEqual(_period(year=" 2025 ", month=" 3 "), (2025, 3))

    def test_only_month_uses_current_year(self):
        self.assertEqual(_period(month="3"), (2026, 3))

    def test_only_year_uses_current_month(self):
        self.assertEqual(_period(year="2025"), (2025, 5))

    def test_non_numeric_falls_back_to_current_month(self):
        self.assertEqual(_period(year="abc", month="3"), (2026, 5))
        self.assertEqual(_period(year="2025", month="abc"), (2026, 5))

    def test_month_zero_and_thirteen_fall_back(self):
        self.assertEqual(_period(year="2025", month="0"), (2026, 5))
        self.assertEqual(_period(year="2025", month="13"), (2026, 5))

    def test_year_out_of_range_falls_back(self):
        self.assertEqual(_period(year=str(MIN_YEAR - 1), month="3"), (2026, 5))
        self.assertEqual(_period(year=str(MAX_YEAR + 1), month="3"), (2026, 5))
        self.assertEqual(_period(year=str(MIN_YEAR), month="3"), (MIN_YEAR, 3))
        self.assertEqual(_period(year=str(MAX_YEAR), month="3"), (MAX_YEAR, 3))

    def test_decimal_falls_back(self):
        self.assertEqual(_period(year="2025.5", month="3"), (2026, 5))
        self.assertEqual(_period(year="2025", month="3.0"), (2026, 5))

    def test_negative_falls_back(self):
        self.assertEqual(_period(year="2025", month="-1"), (2026, 5))


class PeriodQueryViewTests(AuthenticatedTestCase):
    """Parametros invalidos na query nao podem gerar 500 em nenhuma tela."""

    def setUp(self):
        self.goal = Goal.objects.create(
            name="Reserva",
            goal_type=Goal.GoalType.ACCUMULATION,
            target_amount="1000.00",
            start_date=date(2026, 5, 1),
            target_date=date(2026, 12, 31),
        )

    def _urls(self):
        return [
            reverse("transactions:list"),
            reverse("transactions:transfers"),
            reverse("reports:monthly-dashboard-page"),
            reverse("goals:list"),
            reverse("goals:monthly-goals"),
            reverse("goals:detail", kwargs={"goal_id": self.goal.id}),
            reverse("recurrences:forecasts-filter-page"),
        ]

    def test_invalid_year_returns_200(self):
        for url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {"year": "abc"}).status_code, 200)

    def test_invalid_month_returns_200(self):
        for url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {"month": "13"}).status_code, 200)

    def test_issue_urls_do_not_500(self):
        for path in (
            "/goals/monthly/?year=abc",
            "/transactions/?month=13",
            "/reports/month/?year=&month=0",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_invalid_period_context_falls_back_to_current_month(self):
        response = self.client.get(reverse("transactions:list"), {"year": "abc", "month": "3"})
        self.assertTrue(MIN_YEAR <= response.context["year"] <= MAX_YEAR)
        self.assertTrue(1 <= response.context["month"] <= 12)

    def test_reports_invalid_range_falls_back_to_12(self):
        response = self.client.get(
            reverse("reports:monthly-dashboard-page"), {"range": "abc"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["range_months"], 12)
