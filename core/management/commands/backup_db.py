from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from core.backup import backup_database


class Command(BaseCommand):
    help = "Cria um backup consistente do banco SQLite em <pasta do banco>/backups."

    def handle(self, *args, **options):
        if not connection.settings_dict["ENGINE"].endswith("sqlite3"):
            raise CommandError("backup_db so funciona com banco SQLite.")

        target = backup_database(
            connection.settings_dict["NAME"],
            now=timezone.localtime().replace(tzinfo=None),
        )
        self.stdout.write(self.style.SUCCESS(f"Backup criado: {target}"))
