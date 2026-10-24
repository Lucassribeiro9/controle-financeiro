"""Testes do guard da migration 0007 (spec 013, AJU-05)."""

from django.apps import apps as django_apps
from django.db import connection
from django.test import TestCase

from accounts.models import FinancialAccount
from institutions.models import Institution
from transactions.models import Transaction

import importlib

migration = importlib.import_module("transactions.migrations.0007_adjustment_in_out")


class LegacyAdjustmentGuardTests(TestCase):
    """O guard aborta sem alterar dados quando existe `adjustment` legado."""

    def setUp(self):
        institution = Institution.objects.create(name="Inter", code="077")
        self.account = FinancialAccount.objects.create(name="Conta", institution=institution)

    def _legacy(self, description):
        transaction = Transaction.objects.create(
            description=description,
            amount="10.00",
            transaction_type="expense",
            account=self.account,
            date="2026-05-08",
        )
        Transaction.objects.filter(pk=transaction.pk).update(transaction_type="adjustment")
        return transaction

    def test_guard_raises_listing_ids(self):
        first = self._legacy("a")
        second = self._legacy("b")

        with self.assertRaises(RuntimeError) as ctx:
            migration.abort_on_legacy_adjustments(django_apps, connection.schema_editor)

        self.assertIn(f"{first.id}, {second.id}", str(ctx.exception))
        self.assertEqual(Transaction.objects.filter(transaction_type="adjustment").count(), 2)

    def test_guard_passes_without_legacy_adjustments(self):
        migration.abort_on_legacy_adjustments(django_apps, connection.schema_editor)
