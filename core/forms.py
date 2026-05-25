"""Campos reutilizáveis para entrada em formato brasileiro."""

from datetime import date
from decimal import Decimal
from decimal import InvalidOperation

from django import forms


DATE_INPUT_FORMATS = ["%d/%m/%Y", "%Y-%m-%d"]


def normalize_decimal(value):
    """Converte decimal em formato pt-BR ou ISO para Decimal."""

    if value in (None, ""):
        return None

    if isinstance(value, Decimal):
        return value

    normalized_value = str(value).strip()
    if "," in normalized_value:
        normalized_value = normalized_value.replace(".", "").replace(",", ".")

    try:
        return Decimal(normalized_value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor informado é inválido.") from exc


def parse_br_date(value):
    """Converte data em dd/mm/aaaa ou ISO para date."""

    field = forms.DateField(input_formats=DATE_INPUT_FORMATS)
    return field.clean(value)


class BRDateInput(forms.TextInput):
    """Widget textual para datas no formato dd/mm/aaaa."""

    input_type = "text"

    def __init__(self, attrs=None):
        default_attrs = {
            "autocomplete": "off",
            "inputmode": "numeric",
            "pattern": r"\d{2}/\d{2}/\d{4}",
            "placeholder": "dd/mm/aaaa",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def format_value(self, value):
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        return value


class BRDecimalInput(forms.TextInput):
    """Widget textual para decimais no formato brasileiro."""

    input_type = "text"

    def __init__(self, attrs=None):
        default_attrs = {
            "autocomplete": "off",
            "inputmode": "decimal",
            "placeholder": "0,00",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def format_value(self, value):
        if isinstance(value, Decimal):
            return f"{value:.2f}".replace(".", ",")
        return value


class BRIntegerInput(forms.TextInput):
    """Widget textual para inteiros sem controles de incremento."""

    input_type = "text"

    def __init__(self, attrs=None):
        default_attrs = {
            "autocomplete": "off",
            "inputmode": "numeric",
            "pattern": r"\d*",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class BRDecimalField(forms.DecimalField):
    """DecimalField que aceita vírgula decimal e separador de milhar."""

    widget = BRDecimalInput

    def to_python(self, value):
        if value in self.empty_values:
            return None
        return super().to_python(normalize_decimal(value))


class BRDateField(forms.DateField):
    """DateField com entrada dd/mm/aaaa."""

    widget = BRDateInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", DATE_INPUT_FORMATS)
        super().__init__(*args, **kwargs)


class BRIntegerField(forms.IntegerField):
    """IntegerField renderizado como texto para evitar spinners."""

    widget = BRIntegerInput


class AnnualRateField(BRDecimalField):
    """Aceita taxa anual como percentual e persiste em decimal."""

    def to_python(self, value):
        parsed_value = super().to_python(value)
        if parsed_value is None:
            return None
        if parsed_value > Decimal("1"):
            return parsed_value / Decimal("100")
        return parsed_value
