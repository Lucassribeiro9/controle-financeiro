"""Tests das views do app categories."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FinancialAccount
from categories.models import Category
from institutions.models import Institution
from transactions.models import Transaction


class CategoryViewTests(TestCase):
    """Garante telas de listagem, criacao e edicao de categorias."""

    def test_category_list_page_returns_success(self):
        """Deve renderizar a lista de categorias."""

        Category.objects.create(name="Alimentacao")

        response = self.client.get(reverse("categories:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/list.html")
        self.assertContains(response, "Alimentacao")
        self.assertContains(response, "Categoria raiz")
        self.assertContains(response, "Ativa")

    def test_category_list_page_shows_children_count(self):
        """Deve exibir quantidade de subcategorias."""

        parent = Category.objects.create(name="Moradia")
        Category.objects.create(name="Aluguel", parent=parent)
        Category.objects.create(name="Condominio", parent=parent)

        response = self.client.get(reverse("categories:list"))

        parent_summary = next(
            category
            for category in response.context["categories"]
            if category.name == "Moradia"
        )
        self.assertEqual(parent_summary.children_count, 2)
        self.assertContains(response, "Moradia")

    def test_category_create_page_returns_form(self):
        """Deve renderizar formulario de criacao."""

        response = self.client.get(reverse("categories:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/form.html")
        self.assertContains(response, "Nova categoria")

    def test_post_create_root_category(self):
        """Deve criar categoria raiz."""

        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "Alimentacao",
                "parent": "",
                "is_active": "on",
            },
        )
        category = Category.objects.get(name="Alimentacao")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("categories:list"))
        self.assertIsNone(category.parent)
        self.assertTrue(category.is_active)

    def test_post_create_child_category(self):
        """Deve criar subcategoria vinculada a categoria pai."""

        parent = Category.objects.create(name="Moradia")

        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "Aluguel",
                "parent": parent.id,
                "is_active": "on",
            },
        )
        category = Category.objects.get(name="Aluguel")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(category.parent, parent)

    def test_post_update_category_edits_category(self):
        """Deve editar uma categoria."""

        parent = Category.objects.create(name="Casa")
        category = Category.objects.create(name="Aluguel")

        response = self.client.post(
            reverse("categories:update", kwargs={"category_id": category.id}),
            data={
                "name": "Moradia fixa",
                "parent": parent.id,
            },
        )
        category.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(category.name, "Moradia fixa")
        self.assertEqual(category.parent, parent)
        self.assertFalse(category.is_active)

    def test_post_duplicate_name_shows_form_error(self):
        """Deve impedir nome duplicado."""

        Category.objects.create(name="Transporte")

        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "transporte",
                "parent": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/form.html")
        self.assertContains(response, "Já existe uma categoria com este nome.")
        self.assertEqual(Category.objects.count(), 1)

    def test_post_invalid_icon_color_shows_form_error(self):
        """Deve impedir a criacao com icone ou cor invalidos."""
        response = self.client.post(
            reverse("categories:create"),
            data={
                "name": "Lazer",
                "parent": "",
                "icon": "invalid-icon",
                "color": "invalid-color",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/form.html")
        # Deve mostrar o erro do choice
        self.assertContains(response, "Faça uma escolha válida.")
        self.assertEqual(Category.objects.filter(name="Lazer").count(), 0)

    def test_category_list_shows_monthly_spent(self):
        """Deve exibir o gasto mensal por categoria na listagem."""

        institution = Institution.objects.create(name="Inter", code="077")
        account = FinancialAccount.objects.create(
            name="Conta corrente",
            institution=institution,
            account_type=FinancialAccount.AccountType.CHECKING,
            balance=Decimal("1000.00"),
        )
        category = Category.objects.create(name="Alimentacao")

        Transaction.objects.create(
            description="Mercado",
            amount=Decimal("250.00"),
            transaction_type=Transaction.TransactionType.EXPENSE,
            status=Transaction.PaymentStatus.PAID,
            account=account,
            category=category,
            date=date.today(),
        )

        response = self.client.get(reverse("categories:list"))

        self.assertEqual(response.status_code, 200)
        cat_in_context = next(
            c for c in response.context["categories"] if c.name == "Alimentacao"
        )
        self.assertEqual(cat_in_context.monthly_spent, Decimal("250.00"))
        self.assertContains(response, "Gasto (mês)")


class CategoryCreateGoalViewTests(TestCase):
    """Garante o fluxo de criacao de meta mensal a partir de categoria."""

    def setUp(self):
        """Cria categoria base para os testes de view."""

        self.category = Category.objects.create(name="Alimentacao")

    def test_get_create_goal_form_returns_200(self):
        """Deve renderizar o formulario de criacao de meta mensal."""

        response = self.client.get(
            reverse("categories:create_goal", kwargs={"category_id": self.category.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/create_goal.html")
        self.assertContains(response, "Alimentacao")

    def test_post_create_goal_success_redirects(self):
        """POST valido deve redirecionar para a lista de categorias."""

        import datetime

        today = datetime.date.today()

        response = self.client.post(
            reverse("categories:create_goal", kwargs={"category_id": self.category.id}),
            data={
                "target_amount": "300.00",
                "year": today.year,
                "month": today.month,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("categories:list"))

    def test_post_create_goal_success_shows_message(self):
        """POST valido deve exibir mensagem de sucesso apos redirect."""

        import datetime

        today = datetime.date.today()

        response = self.client.post(
            reverse("categories:create_goal", kwargs={"category_id": self.category.id}),
            data={
                "target_amount": "300.00",
                "year": today.year,
                "month": today.month,
            },
            follow=True,
        )

        messages_list = list(response.context["messages"])
        self.assertTrue(len(messages_list) > 0)

    def test_post_create_goal_invalid_amount_shows_error(self):
        """POST com valor zero deve retornar 200 com erro no form."""

        import datetime

        today = datetime.date.today()

        response = self.client.post(
            reverse("categories:create_goal", kwargs={"category_id": self.category.id}),
            data={
                "target_amount": "0.00",
                "year": today.year,
                "month": today.month,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/create_goal.html")
