from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.demo_data import build_demo_data, has_financial_data, reset_financial_data


class Command(BaseCommand):
    help = (
        "Gera 3 meses de dados de exemplo no banco de desenvolvimento. "
        "Use --reset para apagar os dados financeiros antes (usuarios sao preservados)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Apaga os dados financeiros antes de gerar os de exemplo.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo_data so roda em desenvolvimento (DEBUG=True).")

        if options["reset"]:
            reset_financial_data()
        elif has_financial_data():
            raise CommandError(
                "O banco ja tem dados financeiros. Use --reset para apaga-los e regerar."
            )

        build_demo_data()
        self.stdout.write(self.style.SUCCESS("Dados de exemplo gerados."))
