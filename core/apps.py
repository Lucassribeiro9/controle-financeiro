from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .auth import connect_single_user_guard

        connect_single_user_guard()
