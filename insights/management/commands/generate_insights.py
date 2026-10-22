"""Command para gerar os insights de um mes."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from insights.services import generate_monthly_insights


class Command(BaseCommand):
    """Gera sugestoes pendentes a partir das despesas pagas do mes."""

    help = "Gera os insights do mes informado (padrao: mes corrente)."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, help="Ano, por exemplo 2026.")
        parser.add_argument("--month", type=int, help="Mes de 1 a 12.")

    def handle(self, *args, **options):
        today = timezone.localdate()
        year = options["year"] or today.year
        month = options["month"] or today.month

        if not 1 <= month <= 12:
            raise CommandError("O mês deve estar entre 1 e 12.")

        created = generate_monthly_insights(year=year, month=month)
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(created)} insights criados para {month:02d}/{year}."
            )
        )
