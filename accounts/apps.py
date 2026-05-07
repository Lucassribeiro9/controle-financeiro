from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuracao do app de contas financeiras."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
