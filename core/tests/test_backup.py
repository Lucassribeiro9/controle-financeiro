"""Testes do backup consistente do banco SQLite (spec 012)."""

import sqlite3
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase

from core.backup import BACKUP_DIR_NAME, KEEP_BACKUPS, backup_database


def make_database(path):
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, valor TEXT)")
        db.execute("INSERT INTO t (valor) VALUES ('10.50')")
    return Path(path)


class BackupDatabaseTests(SimpleTestCase):
    """Garante copia consistente, nome com data e retencao."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.source = make_database(self.dir / "db.sqlite3")

    def test_creates_readable_copy_in_backups_dir_with_date_in_name(self):
        """A copia fica em <pasta do banco>/backups, com data no nome e os mesmos dados."""

        target = backup_database(self.source, now=datetime(2026, 10, 24, 9, 30, 15))

        self.assertEqual(target.parent, self.dir / BACKUP_DIR_NAME)
        self.assertEqual(target.name, "db-20261024-093015.sqlite3")
        with sqlite3.connect(target) as db:
            self.assertEqual(db.execute("SELECT valor FROM t").fetchall(), [("10.50",)])

    def test_copy_includes_rows_still_in_wal(self):
        """Linhas ainda no arquivo -wal (leitor aberto) entram na copia."""

        reader = sqlite3.connect(self.source)
        self.addCleanup(reader.close)
        reader.execute("SELECT * FROM t").fetchall()
        with sqlite3.connect(self.source) as writer:
            writer.execute("INSERT INTO t (valor) VALUES ('99.99')")

        target = backup_database(self.source, now=datetime(2026, 10, 24, 10, 0, 0))

        with sqlite3.connect(target) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM t").fetchone(), (2,))

    def test_keeps_only_the_most_recent_backups(self):
        """Acima de KEEP_BACKUPS copias, as mais antigas sao removidas."""

        for day in range(1, KEEP_BACKUPS + 4):
            backup_database(self.source, now=datetime(2026, 9, day, 8, 0, 0))

        names = sorted(p.name for p in (self.dir / BACKUP_DIR_NAME).iterdir())
        self.assertEqual(len(names), KEEP_BACKUPS)
        self.assertEqual(names[0], "db-20260904-080000.sqlite3")
        self.assertEqual(names[-1], f"db-202609{KEEP_BACKUPS + 3:02d}-080000.sqlite3")

    def test_retention_ignores_unrelated_files(self):
        """Arquivos fora do padrao de nome nao sao apagados pela retencao."""

        backups = self.dir / BACKUP_DIR_NAME
        backups.mkdir()
        (backups / "notas.txt").write_text("manter")
        for day in range(1, KEEP_BACKUPS + 3):
            backup_database(self.source, now=datetime(2026, 9, day, 8, 0, 0))

        self.assertTrue((backups / "notas.txt").exists())

    def test_missing_database_raises(self):
        """Banco inexistente deve falhar sem criar copia vazia."""

        with self.assertRaises(FileNotFoundError):
            backup_database(self.dir / "nao-existe.sqlite3")


class BackupDbCommandTests(TestCase):
    """Garante que o comando usa o banco configurado e valida o motor."""

    def test_command_backs_up_configured_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = make_database(Path(tmp) / "db.sqlite3")
            out = StringIO()
            with mock.patch.dict(connection.settings_dict, {"NAME": str(source)}):
                call_command("backup_db", stdout=out)

            copies = list((Path(tmp) / BACKUP_DIR_NAME).glob("db-*.sqlite3"))
            self.assertEqual(len(copies), 1)
            self.assertIn(copies[0].name, out.getvalue())

    def test_command_rejects_non_sqlite_engine(self):
        with mock.patch.dict(
            connection.settings_dict, {"ENGINE": "django.db.backends.postgresql"}
        ):
            with self.assertRaisesMessage(CommandError, "SQLite"):
                call_command("backup_db")
