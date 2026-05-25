"""Testes da navegação principal."""

from django.test import TestCase
from django.urls import reverse


class NavigationTests(TestCase):
    """Garante estados ativos e estrutura mobile da navegação."""

    def test_home_navigation_marks_current_item(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="mobile-topbar"')
        self.assertContains(response, "Principal", count=2)
        self.assertContains(response, "Operação", count=2)
        self.assertContains(response, "Dados", count=2)
        self.assertContains(response, "Sistema", count=2)
        self.assertContains(response, 'href="/" aria-current="page"', count=2)

    def test_transactions_navigation_marks_launches_active(self):
        response = self.client.get(reverse("transactions:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'href="/transactions/" aria-current="page"',
            count=2,
        )
        self.assertNotContains(
            response,
            'href="/transactions/transfers/" aria-current="page"',
        )

    def test_transfer_navigation_marks_transfers_active(self):
        response = self.client.get(reverse("transactions:transfers"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'href="/transactions/transfers/" aria-current="page"',
            count=2,
        )
        self.assertNotContains(response, 'href="/transactions/" aria-current="page"')
