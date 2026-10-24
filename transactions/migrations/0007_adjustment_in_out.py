from django.db import migrations, models


def abort_on_legacy_adjustments(apps, schema_editor):
    """Aborta se houver `adjustment` legado: o sinal nao pode ser inferido (spec 013)."""

    Transaction = apps.get_model("transactions", "Transaction")
    ids = list(
        Transaction.objects.filter(transaction_type="adjustment")
        .order_by("id")
        .values_list("id", flat=True)
    )
    if ids:
        raise RuntimeError(
            "Existem lancamentos do tipo 'adjustment' sem sinal definido (ids: "
            f"{', '.join(str(pk) for pk in ids)}). Converta-os para entrada ou saida "
            "antes de aplicar a migration 0007."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0006_transaction_recurrence"),
    ]

    operations = [
        migrations.RunPython(abort_on_legacy_adjustments, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="transaction",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("income", "Receita"),
                    ("expense", "Despesa"),
                    ("adjustment_in", "Ajuste de entrada"),
                    ("adjustment_out", "Ajuste de saída"),
                    ("card_purchase", "Compra no cartão"),
                    ("benefit_purchase", "Compra no benefício"),
                    ("forecast", "Previsão"),
                    ("statement_payment", "Pagamento de fatura"),
                ],
                max_length=20,
                verbose_name="Tipo",
            ),
        ),
    ]
