"""Utilitarios de teste compartilhados entre apps."""

from django.contrib.auth import get_user_model
from django.test import TestCase


class AuthenticatedTestCase(TestCase):
    """TestCase cujo client ja nasce autenticado.

    O login e feito em `_pre_setup`, para valer mesmo quando a subclasse
    sobrescreve `setUp` sem chamar `super()`.
    """

    def _pre_setup(self):
        super()._pre_setup()
        self.user = get_user_model().objects.create_user(
            username="tester", password="senha-de-teste-123"
        )
        self.client.force_login(self.user)
