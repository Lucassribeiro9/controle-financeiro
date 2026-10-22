"""Remove os models do módulo de Rendimentos descontinuado (#196)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rates", "0002_alter_accountyieldconfig_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="AccountYieldConfig"),
        migrations.DeleteModel(name="ReferenceRate"),
    ]
