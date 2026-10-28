"""Command da rotina diaria de manutencao (ADR-013)."""

from django.core.management.base import BaseCommand, CommandError

from core.maintenance import run_daily_maintenance


class Command(BaseCommand):
    """Executa previsoes, faturas, metas e insights de forma idempotente."""

    help = "Executa as rotinas periodicas: previsoes, faturas, metas e insights."

    def handle(self, *args, **options):
        report = run_daily_maintenance()

        failed = []
        for step in report.steps:
            if step.error:
                failed.append(step.name)
                self.stdout.write(self.style.ERROR(f"{step.name}: ERRO - {step.error}"))
            else:
                self.stdout.write(f"{step.name}: {step.count}")

        if failed:
            raise CommandError(f"Passos com falha: {', '.join(failed)}.")

        self.stdout.write(self.style.SUCCESS("Rotina diaria concluida."))
