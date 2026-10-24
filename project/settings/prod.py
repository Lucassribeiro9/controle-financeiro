"""Settings de producao. Falham no startup quando a configuracao e insegura."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE
from .validation import (
    parse_bool,
    parse_csv,
    parse_int,
    validate_debug_disabled,
    validate_secret_key,
)

SECRET_KEY = validate_secret_key(os.environ.get("DJANGO_SECRET_KEY"))

validate_debug_disabled(os.environ.get("DJANGO_DEBUG"))
DEBUG = False

ALLOWED_HOSTS = parse_csv(os.environ.get("DJANGO_ALLOWED_HOSTS"))
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS e obrigatoria em producao "
        "(hosts separados por virgula, ex.: app.example.com)."
    )

# Banco SQLite em volume persistente (ADR-008). WAL deixa leituras e escrita
# coexistirem entre os workers; IMMEDIATE evita deadlock ao promover leitura
# para escrita; timeout de 20 s espera o lock em vez de dar "database is locked".
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH") or "/data/db.sqlite3",
        "OPTIONS": {
            "timeout": 20,
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
        },
    }
}

CSRF_TRUSTED_ORIGINS = parse_csv(os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS"))

# Arquivos estaticos servidos pelo proprio app via WhiteNoise.
# Se for necessario, um proxy como Nginx pode assumir /static/ no futuro.
MIDDLEWARE = [
    MIDDLEWARE[0],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# HTTPS: cookies seguros e redirect. Atras de proxy que termina TLS, defina
# DJANGO_SECURE_PROXY_SSL_HEADER=true para confiar em X-Forwarded-Proto.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
if parse_bool(os.environ.get("DJANGO_SECURE_PROXY_SSL_HEADER")):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS conservador (1 hora) ate o HTTPS estar validado; aumente por variavel.
# includeSubDomains/preload ficam desligados de proposito: sao dificeis de
# desfazer, entao W005 e W021 sao silenciados ate existir um deploy validado.
SECURE_HSTS_SECONDS = parse_int(
    "DJANGO_SECURE_HSTS_SECONDS",
    os.environ.get("DJANGO_SECURE_HSTS_SECONDS"),
    default=3600,
)
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
