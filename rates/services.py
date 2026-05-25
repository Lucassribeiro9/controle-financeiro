"""Regras de negocio para taxas e estimativas de rendimento."""

from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from .models import AccountYieldConfig, ReferenceRate


MONEY = Decimal("0.01")
RATE_PRECISION = Decimal("0.00000001")


def save_reference_rate(
    *,
    date,
    value,
    notes="",
    source="manual",
    rate_type=ReferenceRate.RateType.CDI,
    periodicity=ReferenceRate.Periodicity.ANNUAL,
):
    """Salva taxa de referencia manual validada."""

    reference_rate = ReferenceRate(
        rate_type=rate_type,
        date=date,
        value=value,
        periodicity=periodicity,
        source=source,
        notes=notes,
    )
    reference_rate.full_clean()
    reference_rate.save()
    return reference_rate


def get_latest_reference_rate(*, rate_type):
    """Busca a ultima taxa de referencia de um tipo."""

    reference_rate = (
        ReferenceRate.objects.filter(rate_type=rate_type)
        .order_by("-date", "-created_at")
        .first()
    )
    if reference_rate is None:
        raise ValidationError({"rate": "Nenhuma taxa de referencia cadastrada."})

    return reference_rate


def get_latest_cdi_rate():
    """Busca o ultimo CDI anual cadastrado."""

    return get_latest_reference_rate(rate_type=ReferenceRate.RateType.CDI)


def simulate_cdi_yield(
    *,
    amount,
    months,
    annual_cdi_rate,
    cdi_percentage,
):
    """Simula rendimento composto por percentual do CDI anual."""

    _validate_positive(
        value=amount,
        field_name="amount",
        message="Valor inicial deve ser maior que zero.",
    )
    _validate_positive(
        value=Decimal(months),
        field_name="months",
        message="Meses deve ser maior que zero.",
    )
    _validate_positive(
        value=annual_cdi_rate,
        field_name="annual_cdi_rate",
        message="CDI anual deve ser maior que zero.",
    )
    _validate_positive(
        value=cdi_percentage,
        field_name="cdi_percentage",
        message="Percentual do CDI deve ser maior que zero.",
    )

    months = int(months)
    cdi_multiplier = cdi_percentage / Decimal("100")
    effective_annual_rate = annual_cdi_rate * cdi_multiplier
    monthly_rate = _calculate_monthly_rate(effective_annual_rate=effective_annual_rate)
    final_amount = amount * ((Decimal("1") + monthly_rate) ** months)
    final_amount = final_amount.quantize(MONEY)
    initial_amount = amount.quantize(MONEY)
    estimated_yield = (final_amount - initial_amount).quantize(MONEY)

    return {
        "initial_amount": initial_amount,
        "final_amount": final_amount,
        "estimated_yield": estimated_yield,
        "annual_cdi_rate": annual_cdi_rate,
        "cdi_percentage": cdi_percentage,
        "effective_annual_rate": effective_annual_rate.quantize(RATE_PRECISION),
        "monthly_rate": monthly_rate.quantize(RATE_PRECISION),
        "months": months,
    }


def estimate_account_yield(*, account, months, amount=None):
    """Estima rendimento de uma conta a partir da sua configuracao."""

    initial_amount = amount if amount is not None else account.balance
    _validate_positive(
        value=initial_amount,
        field_name="amount",
        message="Valor inicial deve ser maior que zero.",
    )
    _validate_positive(
        value=Decimal(months),
        field_name="months",
        message="Meses deve ser maior que zero.",
    )

    try:
        yield_config = account.yield_config
    except ObjectDoesNotExist as exc:
        raise ValidationError(
            {"yield_config": "Conta não possui configuração de rendimento."}
        ) from exc

    if not yield_config.is_active:
        raise ValidationError({"yield_config": "Configuração de rendimento está inativa."})

    if yield_config.yield_type == AccountYieldConfig.YieldType.NONE:
        initial_amount = initial_amount.quantize(MONEY)
        return {
            "account": account,
            "initial_amount": initial_amount,
            "final_amount": initial_amount,
            "estimated_yield": Decimal("0.00"),
            "months": int(months),
            "rate": None,
            "yield_config": yield_config,
        }

    if yield_config.yield_type == AccountYieldConfig.YieldType.CDI_PERCENTAGE:
        cdi_rate = get_latest_cdi_rate()
        estimate = simulate_cdi_yield(
            amount=initial_amount,
            months=months,
            annual_cdi_rate=cdi_rate.value,
            cdi_percentage=yield_config.cdi_percentage,
        )
        return {
            "account": account,
            "rate": cdi_rate,
            "yield_config": yield_config,
            **estimate,
        }

    raise ValidationError({"yield_type": "Tipo de rendimento inválido."})


def _calculate_monthly_rate(*, effective_annual_rate):
    """Converte taxa anual efetiva em taxa mensal equivalente."""

    return (
        (Decimal("1") + effective_annual_rate) ** (Decimal("1") / Decimal("12"))
    ) - Decimal("1")


def _validate_positive(*, value, field_name, message):
    """Valida valor positivo."""

    if value <= Decimal("0"):
        raise ValidationError({field_name: message})
