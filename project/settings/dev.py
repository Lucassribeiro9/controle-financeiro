"""Settings de desenvolvimento local. Nao use em producao."""

from .base import *  # noqa: F401,F403

# Chave explicitamente insegura: o validador de producao a rejeita.
SECRET_KEY = "django-insecure-dev-only-change-me"

DEBUG = True

ALLOWED_HOSTS = [
    "0.0.0.0",
    "localhost",
    "127.0.0.1",
]
