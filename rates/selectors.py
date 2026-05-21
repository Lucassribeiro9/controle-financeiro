"""Seletores para taxas e rendimentos."""

from django.core.exceptions import ValidationError

from .models import AccountYieldConfig, ReferenceRate
from .services import estimate_account_yield, get_latest_reference_rate


def get_latest_rates() -> dict:
    """Retorna a ultima taxa disponivel por tipo."""

    latest_rates = {}
    for rate_type, _label in ReferenceRate.RateType.choices:
        try:
            latest_rates[rate_type] = get_latest_reference_rate(rate_type=rate_type)
        except ValidationError:
            latest_rates[rate_type] = None
    return latest_rates


def get_rate_history(rate_type):
    """Lista historico de taxas de um tipo."""

    return ReferenceRate.objects.filter(rate_type=rate_type).order_by("-date", "-created_at")


def get_active_yield_configs():
    """Lista configuracoes ativas de rendimento."""

    return (
        AccountYieldConfig.objects.filter(is_active=True)
        .select_related("account", "account__institution")
        .order_by("account__name")
    )


def get_account_yield_summary(*, months):
    """Lista estimativas de rendimento por conta configurada."""

    summary = []
    for config in get_active_yield_configs():
        try:
            estimate = estimate_account_yield(
                account=config.account,
                months=months,
            )
        except ValidationError as exc:
            summary.append(
                {
                    "config": config,
                    "estimate": None,
                    "error": _validation_error_to_text(exc),
                }
            )
        else:
            summary.append(
                {
                    "config": config,
                    "estimate": estimate,
                    "error": "",
                }
            )
    return summary


def _validation_error_to_text(exc):
    """Converte ValidationError em texto curto para exibicao."""

    if hasattr(exc, "message_dict"):
        return "; ".join(
            error
            for errors in exc.message_dict.values()
            for error in errors
        )
    return "; ".join(exc.messages)
