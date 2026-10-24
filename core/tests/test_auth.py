"""Testes de autenticacao obrigatoria nas rotas financeiras."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from core.auth import ApiAwareLoginRequiredMiddleware, api_login_required

PUBLIC_ROUTES = {"login/", "health/"}
ADMIN_PREFIX = "admin/"

JSON_ROUTES = [
    ("get", "insights:list", {}),
    ("get", "insights:recent", {}),
    ("get", "imports:review", {}),
    ("post", "imports:upload", {}),
    ("post", "imports:confirm", {"imported_transaction_id": 1}),
    ("post", "imports:discard", {"imported_transaction_id": 1}),
    ("get", "recurrences:monthly-forecasts", {"year": 2026, "month": 1}),
]


def _iter_patterns(patterns, prefix=""):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _iter_patterns(
                entry.url_patterns, prefix + str(entry.pattern)
            )
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry


class RouteProtectionTests(SimpleTestCase):
    """Garante que nenhuma rota de negocio fica sem protecao."""

    def test_middleware_is_enabled_after_authentication(self):
        middleware = settings.MIDDLEWARE
        auth = middleware.index(
            "django.contrib.auth.middleware.AuthenticationMiddleware"
        )
        login = middleware.index("core.auth.ApiAwareLoginRequiredMiddleware")
        self.assertGreater(login, auth)

    def test_only_expected_routes_are_public(self):
        public = {
            route
            for route, entry in _iter_patterns(get_resolver().url_patterns)
            if not route.startswith(ADMIN_PREFIX)
            and getattr(entry.callback, "login_required", True) is False
        }
        self.assertEqual(public, PUBLIC_ROUTES)


class AnonymousAccessTests(TestCase):
    """Anonimo e redirecionado (HTML) ou recebe 401 (JSON)."""

    def test_every_html_route_redirects_anonymous_to_login(self):
        checked = 0
        for route, entry in _iter_patterns(get_resolver().url_patterns):
            if route.startswith(ADMIN_PREFIX) or not entry.name:
                continue
            if getattr(entry.callback, "login_required", True) is False:
                continue
            if getattr(entry.callback, "api_login_required", False):
                continue
            with self.subTest(route=route):
                response = self.client.get("/" + _fill(route))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/login/?next="))
                checked += 1
        self.assertGreater(checked, 30)

    def test_anonymous_post_to_html_mutation_redirects_and_changes_nothing(self):
        from accounts.models import FinancialAccount

        response = self.client.post(reverse("accounts:create"), {"name": "X"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/"))
        self.assertFalse(FinancialAccount.objects.exists())

    def test_bulk_review_redirects_anonymous(self):
        response = self.client.post(reverse("imports:bulk-review"), {})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/"))

    def test_json_routes_return_401_for_anonymous(self):
        for method, name, kwargs in JSON_ROUTES:
            with self.subTest(route=name):
                response = getattr(self.client, method)(reverse(name, kwargs=kwargs))
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["Content-Type"], "application/json")
                self.assertIn("error", response.json())

    def test_json_routes_are_marked_as_api(self):
        for _, name, kwargs in JSON_ROUTES:
            with self.subTest(route=name):
                match = get_resolver().resolve(reverse(name, kwargs=kwargs))
                self.assertTrue(getattr(match.func, "api_login_required", False))

    def test_health_check_stays_public(self):
        self.assertEqual(self.client.get(reverse("core:health-check")).status_code, 200)

    def test_login_page_is_public_without_navigation(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertNotContains(response, "app-nav-link")

    def test_admin_keeps_its_own_login(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


class AuthenticatedAccessTests(TestCase):
    """Usuario autenticado acessa os fluxos e logout exige POST."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="lucas", password="senha-de-teste-123"
        )

    def test_authenticated_user_reaches_home_and_json_route(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("insights:list")).status_code, 200)

    def test_wrong_method_returns_405_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("imports:upload"))
        self.assertEqual(response.status_code, 405)

    def test_login_redirects_to_next(self):
        response = self.client.post(
            reverse("login") + "?next=/accounts/",
            {"username": "lucas", "password": "senha-de-teste-123", "next": "/accounts/"},
        )
        self.assertRedirects(response, "/accounts/", fetch_redirect_response=False)

    def test_login_ignores_external_next(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "lucas",
                "password": "senha-de-teste-123",
                "next": "//evil.example.com/",
            },
        )
        self.assertRedirects(
            response, reverse("core:home"), fetch_redirect_response=False
        )

    def test_invalid_credentials_show_error(self):
        response = self.client.post(
            reverse("login"), {"username": "lucas", "password": "errada"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "app-message")

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 302)

    def test_navigation_shows_logout_form_when_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, reverse("logout"))

    def test_csrf_is_enforced_on_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse("accounts:create"), {"name": "X"})
        self.assertEqual(response.status_code, 403)
        response = client.post(
            reverse("recurrences:ignore-forecast", kwargs={"transaction_id": 1})
        )
        self.assertEqual(response.status_code, 403)


class ApiLoginDecoratorTests(SimpleTestCase):
    def test_decorator_marks_view_and_returns_it(self):
        def view(request):
            return None

        self.assertIs(api_login_required(view), view)
        self.assertTrue(view.api_login_required)

    def test_middleware_class_is_exposed(self):
        self.assertTrue(hasattr(ApiAwareLoginRequiredMiddleware, "handle_no_permission"))


def _fill(route: str) -> str:
    """Troca conversores de path por valores de exemplo."""

    import re

    route = re.sub(r"<int:[^>]+>", "1", route)
    route = re.sub(r"<slug:[^>]+>", "x", route)
    return re.sub(r"<[^>]+>", "x", route)


class ApiNotFoundTests(TestCase):
    """Views JSON respondem 404 em JSON; views HTML mantem o 404 padrao."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="lucas", password="senha-de-teste-123"
        )
        self.client.force_login(self.user)

    def test_json_routes_with_missing_id_return_json_404(self):
        routes = [
            ("post", "imports:confirm", {"imported_transaction_id": 999999}),
            ("post", "imports:discard", {"imported_transaction_id": 999999}),
        ]
        for method, name, kwargs in routes:
            with self.subTest(route=name):
                response = getattr(self.client, method)(reverse(name, kwargs=kwargs))
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response["Content-Type"], "application/json")
                self.assertIn("error", response.json())

    def test_html_route_with_missing_id_keeps_default_404(self):
        response = self.client.get(reverse("accounts:update", kwargs={"account_id": 999999}))
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response["Content-Type"], "application/json")
