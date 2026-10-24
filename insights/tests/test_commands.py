"""Tests do command generate_insights."""

from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from insights.models import Insight
from core.demo_data import build_realistic_month


class GenerateInsightsCommandTests(TestCase):
    """Garante argumentos, saida e idempotencia do command."""

    def setUp(self):
        build_realistic_month(year=2026, month=5)

    def _run(self, *args):
        out = StringIO()
        call_command("generate_insights", *args, stdout=out)
        return out.getvalue()

    def test_creates_insights_for_given_month(self):
        output = self._run("--year", "2026", "--month", "5")

        self.assertIn("5 insights criados para 05/2026", output)
        self.assertEqual(Insight.objects.count(), 5)

    def test_second_run_reports_zero(self):
        self._run("--year", "2026", "--month", "5")

        output = self._run("--year", "2026", "--month", "5")

        self.assertIn("0 insights criados para 05/2026", output)
        self.assertEqual(Insight.objects.count(), 5)

    def test_defaults_to_current_month(self):
        with mock.patch(
            "insights.management.commands.generate_insights.timezone.localdate",
            return_value=date(2026, 5, 20),
        ):
            output = self._run()

        self.assertIn("5 insights criados para 05/2026", output)

    def test_invalid_month_raises_command_error(self):
        with self.assertRaises(CommandError):
            self._run("--year", "2026", "--month", "13")
        self.assertEqual(Insight.objects.count(), 0)
