"""Testes da invariante single-user: exatamente um usuario ativo."""

from io import StringIO

from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "senha-de-teste-123"


class SingleUserGuardTests(TestCase):
    """Impede a existencia de um segundo usuario ativo."""

    def test_first_active_user_can_be_created(self):
        user = User.objects.create_user(username="dono", password=PASSWORD)
        self.assertTrue(user.is_active)

    def test_second_active_user_is_rejected(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        with self.assertRaises(ValidationError):
            User.objects.create_user(username="intruso", password=PASSWORD)
        self.assertEqual(User.objects.count(), 1)

    def test_second_inactive_user_is_allowed(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        extra = User.objects.create_user(
            username="antigo", password=PASSWORD, is_active=False
        )
        self.assertFalse(extra.is_active)

    def test_reactivating_user_with_another_active_is_rejected(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        extra = User.objects.create_user(
            username="antigo", password=PASSWORD, is_active=False
        )
        extra.is_active = True
        with self.assertRaises(ValidationError):
            extra.save()

    def test_updating_the_only_active_user_is_allowed(self):
        user = User.objects.create_user(username="dono", password=PASSWORD)
        user.first_name = "Dono"
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Dono")

    def test_createsuperuser_fails_with_clear_message_for_second_user(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "createsuperuser",
                interactive=False,
                username="outro",
                email="outro@example.com",
                stdout=StringIO(),
            )
        self.assertIn("usuario ativo", str(ctx.exception))
        self.assertFalse(User.objects.filter(username="outro").exists())


class SingleUserBackendTests(TestCase):
    """Autenticacao falha fechado quando ha mais de um usuario ativo."""

    def test_single_active_user_authenticates(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        self.assertIsNotNone(authenticate(username="dono", password=PASSWORD))

    def test_inactive_extra_user_does_not_block_owner(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        User.objects.create_user(username="antigo", password=PASSWORD, is_active=False)
        self.assertIsNotNone(authenticate(username="dono", password=PASSWORD))

    def test_nobody_authenticates_with_two_active_users(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        # Contorna o guard, simulando insercao direta no banco.
        User.objects.bulk_create(
            [User(username="intruso", password="x", is_active=True)]
        )
        self.assertEqual(User.objects.filter(is_active=True).count(), 2)
        for username in ("dono", "intruso"):
            with self.subTest(username=username):
                self.assertIsNone(authenticate(username=username, password=PASSWORD))

    def test_wrong_password_does_not_authenticate(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        self.assertIsNone(authenticate(username="dono", password="errada"))

    def test_login_view_creates_no_session_with_two_active_users(self):
        User.objects.create_user(username="dono", password=PASSWORD)
        User.objects.bulk_create(
            [User(username="intruso", password="x", is_active=True)]
        )
        response = self.client.post(
            reverse("login"), {"username": "dono", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_blocked_with_two_active_users(self):
        owner = User.objects.create_superuser(
            username="dono", email="d@example.com", password=PASSWORD
        )
        User.objects.bulk_create(
            [User(username="intruso", password="x", is_active=True)]
        )
        response = self.client.post(
            "/admin/login/",
            {"username": owner.username, "password": PASSWORD, "next": "/admin/"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
