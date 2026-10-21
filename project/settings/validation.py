"""Validacoes de configuracao usadas pelo settings de producao."""

from django.core.exceptions import ImproperlyConfigured

MIN_SECRET_KEY_LENGTH = 50
MIN_SECRET_KEY_UNIQUE_CHARS = 5
INSECURE_SECRET_KEY_PREFIX = "django-insecure-"
KNOWN_INSECURE_SECRET_KEYS = ("change-me", "changeme", "secret", "password")
TRUE_VALUES = ("1", "true", "yes", "on")


def validate_secret_key(value: str | None) -> str:
    """Garante que a chave existe, e longa, variada e nao e um valor conhecido."""

    key = (value or "").strip()
    if not key:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY e obrigatoria em producao. Gere uma com: "
            'python -c "import secrets; print(secrets.token_urlsafe(50))"'
        )

    lowered = key.lower()
    if lowered.startswith(INSECURE_SECRET_KEY_PREFIX) or any(
        known in lowered for known in KNOWN_INSECURE_SECRET_KEYS
    ):
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY usa um valor padrao/conhecido e nao pode ser usada "
            "em producao."
        )

    if len(key) < MIN_SECRET_KEY_LENGTH:
        raise ImproperlyConfigured(
            f"DJANGO_SECRET_KEY deve ter pelo menos {MIN_SECRET_KEY_LENGTH} caracteres."
        )

    if len(set(key)) < MIN_SECRET_KEY_UNIQUE_CHARS:
        raise ImproperlyConfigured(
            f"DJANGO_SECRET_KEY deve ter pelo menos {MIN_SECRET_KEY_UNIQUE_CHARS} "
            "caracteres distintos."
        )

    return key


def validate_debug_disabled(value: str | None) -> None:
    """Falha se DJANGO_DEBUG pedir debug ligado em producao."""

    if parse_bool(value):
        raise ImproperlyConfigured(
            "DJANGO_DEBUG nao pode ser verdadeiro em producao. Remova a variavel."
        )


def parse_bool(value: str | None) -> bool:
    """Converte texto de variavel de ambiente em booleano."""

    return (value or "").strip().lower() in TRUE_VALUES


def parse_csv(value: str | None) -> list[str]:
    """Converte uma lista separada por virgula ignorando espacos e itens vazios."""

    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_int(name: str, value: str | None, *, default: int) -> int:
    """Converte um inteiro nao negativo ou falha citando a variavel."""

    if value is None or not value.strip():
        return default

    try:
        number = int(value)
    except ValueError:
        number = -1
    if number < 0:
        raise ImproperlyConfigured(f"{name} deve ser um inteiro maior ou igual a zero.")
    return number
