"""Testes das settings de desenvolvimento e producao e da validacao de secrets."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from project.settings.validation import (
    parse_bool,
    parse_csv,
    parse_int,
    validate_debug_disabled,
    validate_secret_key,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ValidateSecretKeyTests(SimpleTestCase):
    """Garante que a chave de producao e obrigatoria, longa e nao conhecida."""

    def test_accepts_generated_key(self):
        """Uma chave gerada com secrets deve ser aceita."""

        key = secrets.token_urlsafe(50)

        self.assertEqual(validate_secret_key(key), key)

    def test_rejects_missing_or_empty_key(self):
        """Chave ausente ou vazia deve falhar citando a variavel."""

        for value in [None, "", "   "]:
            with self.subTest(value=value):
                with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_SECRET_KEY"):
                    validate_secret_key(value)

    def test_rejects_short_key(self):
        """Chave curta demais deve ser rejeitada."""

        with self.assertRaisesMessage(ImproperlyConfigured, "50"):
            validate_secret_key(secrets.token_urlsafe(20))

    def test_rejects_key_with_low_character_variety(self):
        """Chave longa mas com poucos caracteres distintos deve ser rejeitada."""

        with self.assertRaisesMessage(ImproperlyConfigured, "distintos"):
            validate_secret_key("ab" * 40)

    def test_rejects_known_default_values(self):
        """Valores padrao conhecidos devem ser rejeitados mesmo se alongados."""

        for value in [
            "change-me",
            "django-insecure-dev-only-change-me",
            "django-insecure-" + secrets.token_urlsafe(50),
            "change-me" * 10,
        ]:
            with self.subTest(value=value):
                with self.assertRaises(ImproperlyConfigured):
                    validate_secret_key(value)


class ParsingHelpersTests(SimpleTestCase):
    """Garante o parse de variaveis de ambiente usadas pelo settings de producao."""

    def test_parse_bool(self):
        """Deve reconhecer valores verdadeiros comuns e tratar o resto como falso."""

        for value in ["1", "true", "True", "YES", "on"]:
            self.assertTrue(parse_bool(value), value)
        for value in [None, "", "0", "false", "no", "off", "qualquer"]:
            self.assertFalse(parse_bool(value), value)

    def test_parse_csv_strips_blanks(self):
        """Deve separar por virgula ignorando espacos e itens vazios."""

        self.assertEqual(parse_csv(" a.com, ,b.com,"), ["a.com", "b.com"])
        self.assertEqual(parse_csv(None), [])

    def test_parse_int_uses_default_and_rejects_invalid(self):
        """Deve usar o default quando ausente e falhar para valores invalidos."""

        self.assertEqual(parse_int("DJANGO_X", None, default=3600), 3600)
        self.assertEqual(parse_int("DJANGO_X", "7200", default=3600), 7200)
        with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_X"):
            parse_int("DJANGO_X", "abc", default=3600)
        with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_X"):
            parse_int("DJANGO_X", "-1", default=3600)

    def test_validate_debug_disabled(self):
        """Debug verdadeiro em producao deve falhar; ausente ou falso passa."""

        validate_debug_disabled(None)
        validate_debug_disabled("False")
        for value in ["1", "true", "True", "on"]:
            with self.subTest(value=value):
                with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_DEBUG"):
                    validate_debug_disabled(value)


def run_python(code, *, env=None, settings_module=None):
    """Executa codigo em subprocesso limpo, como no startup real do servidor."""

    process_env = {"PATH": os.environ.get("PATH", "")}
    if settings_module:
        process_env["DJANGO_SETTINGS_MODULE"] = settings_module
    process_env.update(env or {})
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BASE_DIR,
        env=process_env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def valid_prod_env(**overrides):
    env = {
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
        "DJANGO_ALLOWED_HOSTS": "app.example.com",
    }
    env.update(overrides)
    return env


LOAD_SETTINGS = "from django.conf import settings; settings.SECRET_KEY"


class ProdSettingsStartupTests(SimpleTestCase):
    """Garante que o startup de producao falha de forma clara quando insegura."""

    prod = "project.settings.prod"

    def assert_startup_fails(self, env, expected_message):
        result = run_python(LOAD_SETTINGS, env=env, settings_module=self.prod)

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertIn(expected_message, result.stderr)

    def test_fails_without_secret_key(self):
        """Sem DJANGO_SECRET_KEY o startup deve falhar."""

        env = valid_prod_env()
        del env["DJANGO_SECRET_KEY"]

        self.assert_startup_fails(env, "DJANGO_SECRET_KEY")

    def test_fails_with_default_secret_key(self):
        """Com a chave default de desenvolvimento o startup deve falhar."""

        env = valid_prod_env(DJANGO_SECRET_KEY="django-insecure-dev-only-change-me")

        self.assert_startup_fails(env, "DJANGO_SECRET_KEY")

    def test_fails_with_debug_enabled(self):
        """DJANGO_DEBUG verdadeiro em producao deve falhar."""

        self.assert_startup_fails(valid_prod_env(DJANGO_DEBUG="True"), "DJANGO_DEBUG")

    def test_fails_without_allowed_hosts(self):
        """Sem DJANGO_ALLOWED_HOSTS o startup deve falhar."""

        env = valid_prod_env()
        del env["DJANGO_ALLOWED_HOSTS"]

        self.assert_startup_fails(env, "DJANGO_ALLOWED_HOSTS")

    def test_starts_with_valid_configuration(self):
        """Com configuracao valida o startup deve funcionar e manter DEBUG desligado."""

        code = (
            "from django.conf import settings; "
            "print(settings.DEBUG, settings.ALLOWED_HOSTS, settings.SESSION_COOKIE_SECURE, "
            "settings.CSRF_COOKIE_SECURE, settings.SECURE_SSL_REDIRECT, "
            "settings.SECURE_HSTS_SECONDS)"
        )

        result = run_python(code, env=valid_prod_env(), settings_module=self.prod)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "False ['app.example.com'] True True True 3600",
        )

    def test_hsts_seconds_and_proxy_header_come_from_environment(self):
        """HSTS e o header de proxy HTTPS devem ser configuraveis por ambiente."""

        code = (
            "from django.conf import settings; "
            "print(settings.SECURE_HSTS_SECONDS, settings.SECURE_PROXY_SSL_HEADER, "
            "settings.CSRF_TRUSTED_ORIGINS)"
        )
        env = valid_prod_env(
            DJANGO_SECURE_HSTS_SECONDS="86400",
            DJANGO_SECURE_PROXY_SSL_HEADER="true",
            DJANGO_CSRF_TRUSTED_ORIGINS="https://app.example.com",
        )

        result = run_python(code, env=env, settings_module=self.prod)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "86400 ('HTTP_X_FORWARDED_PROTO', 'https') ['https://app.example.com']",
        )

    def test_serves_static_files_with_whitenoise(self):
        """Producao deve servir estaticos via WhiteNoise a partir de STATIC_ROOT."""

        code = (
            "from django.conf import settings; "
            "print('whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE, "
            "settings.STATIC_ROOT)"
        )

        result = run_python(code, env=valid_prod_env(), settings_module=self.prod)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("True "), result.stdout)
        self.assertIn("staticfiles", result.stdout)

    def test_check_deploy_passes_without_warnings(self):
        """check --deploy com settings de producao nao deve ter alertas."""

        result = subprocess.run(
            [
                sys.executable,
                "manage.py",
                "check",
                "--deploy",
                "--fail-level",
                "WARNING",
            ],
            cwd=BASE_DIR,
            env={
                "PATH": os.environ.get("PATH", ""),
                "DJANGO_SETTINGS_MODULE": self.prod,
                **valid_prod_env(),
            },
            capture_output=True,
            text=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ProdDatabaseSettingsTests(SimpleTestCase):
    """Garante o banco de producao persistente (spec 012 / ADR-008)."""

    prod = "project.settings.prod"
    PRINT_DB = (
        "from django.conf import settings; d = settings.DATABASES['default']; "
        "print(d['NAME']); print(d['OPTIONS'])"
    )

    def test_database_path_defaults_to_data_volume(self):
        """Sem DJANGO_DB_PATH o banco fica em /data/db.sqlite3."""

        result = run_python(self.PRINT_DB, env=valid_prod_env(), settings_module=self.prod)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], "/data/db.sqlite3")

    def test_database_path_comes_from_environment(self):
        """DJANGO_DB_PATH sobrescreve o caminho do banco."""

        env = valid_prod_env(DJANGO_DB_PATH="/outro/banco.sqlite3")

        result = run_python(self.PRINT_DB, env=env, settings_module=self.prod)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], "/outro/banco.sqlite3")

    def test_database_uses_wal_and_busy_timeout(self):
        """Producao liga WAL e espera locks por ate 20 s."""

        result = run_python(self.PRINT_DB, env=valid_prod_env(), settings_module=self.prod)

        options = result.stdout.splitlines()[1]
        self.assertIn("journal_mode=WAL", options)
        self.assertIn("'timeout': 20", options)
        self.assertIn("'transaction_mode': 'IMMEDIATE'", options)

    def test_dev_database_stays_in_project_dir(self):
        """Dev continua com db.sqlite3 na raiz do projeto."""

        code = self.PRINT_DB.replace("d['OPTIONS']", "d.get('OPTIONS')")

        result = run_python(code, settings_module="project.settings.dev")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], str(BASE_DIR / "db.sqlite3"))


class DefaultSettingsModuleTests(SimpleTestCase):
    """Garante qual settings cada ponto de entrada carrega por padrao."""

    def test_manage_py_defaults_to_dev_without_environment(self):
        """manage.py deve funcionar localmente sem nenhuma variavel de ambiente."""

        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=BASE_DIR,
            env={"PATH": os.environ.get("PATH", "")},
            capture_output=True,
            text=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dev_settings_enable_debug_with_insecure_key(self):
        """Dev deve manter DEBUG ligado e uma chave explicitamente insegura."""

        code = (
            "from django.conf import settings; "
            "print(settings.DEBUG, settings.SECRET_KEY.startswith('django-insecure-'))"
        )

        result = run_python(code, settings_module="project.settings.dev")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True True")

    def test_wsgi_and_asgi_default_to_prod_and_fail_without_secrets(self):
        """Entradas de servidor devem carregar prod e falhar sem configuracao."""

        for module in ["project.wsgi", "project.asgi"]:
            with self.subTest(module=module):
                result = run_python(f"import {module}")

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_wsgi_loads_with_valid_prod_environment(self):
        """wsgi deve carregar normalmente com configuracao de producao valida."""

        result = run_python("import project.wsgi", env=valid_prod_env())

        self.assertEqual(result.returncode, 0, result.stderr)
