"""Forms do app imports."""

from django import forms

from core.forms import BRDateField

# Filtros recolhiveis da revisao (a busca `q` fica fora do <details>).
COUNTED_FILTER_KEYS = (
    "source_file_name",
    "source_type",
    "account_id",
    "category_id",
    "transaction_type",
)
DATE_KEYS = ("start_date", "end_date")


class ImportReviewFilterForm(forms.Form):
    """Filtros de data da revisao em dd/mm/aaaa, ainda aceitando ISO.

    O selector continua recebendo datas ISO; data invalida vira erro no campo e
    o filtro e ignorado (nunca 500).
    """

    start_date = BRDateField(required=False, label="Início")
    end_date = BRDateField(required=False, label="Fim")

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for key in DATE_KEYS:
                parsed = self._parse(data.get(key))
                if parsed:
                    data[key] = parsed.strftime("%d/%m/%Y")
        super().__init__(data, *args, **kwargs)
        self._params = data

    @classmethod
    def _parse(cls, value):
        if not value:
            return None
        try:
            return cls.base_fields["start_date"].clean(value)
        except forms.ValidationError:
            return None

    def date_filters(self) -> dict:
        """Datas validas em ISO, prontas para o selector."""

        cleaned = getattr(self, "cleaned_data", {})
        return {key: cleaned[key].isoformat() for key in DATE_KEYS if cleaned.get(key)}

    def merge_into(self, filters: dict) -> dict:
        """Troca as datas cruas de `filters` pelas datas validas em ISO."""

        merged = {key: value for key, value in filters.items() if key not in DATE_KEYS}
        merged.update(self.date_filters())
        return merged

    @property
    def active_count(self) -> int:
        """Quantos dos sete filtros recolhiveis estao preenchidos e validos."""

        params = self._params or {}
        selects = sum(1 for key in COUNTED_FILTER_KEYS if params.get(key))
        return selects + len(self.date_filters())
