"""Backup consistente do banco SQLite (spec 012 / ADR-008)."""

import sqlite3
from datetime import datetime
from pathlib import Path

BACKUP_DIR_NAME = "backups"
BACKUP_PREFIX = "db-"
BACKUP_SUFFIX = ".sqlite3"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
KEEP_BACKUPS = 14


def backup_database(source, *, now=None, keep=KEEP_BACKUPS):
    """Copia o banco com a API de backup do SQLite e aplica a retencao.

    Funciona com o app rodando: a API respeita o WAL, ao contrario de copiar o
    arquivo cru. A copia vai para `<pasta do banco>/backups`.
    """

    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"Banco nao encontrado: {source}")

    now = now or datetime.now()
    backup_dir = source.parent / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    target = backup_dir / (
        f"{BACKUP_PREFIX}{now.strftime(BACKUP_TIMESTAMP_FORMAT)}{BACKUP_SUFFIX}"
    )

    origin = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    destination = sqlite3.connect(target)
    try:
        origin.backup(destination)
    except Exception:
        destination.close()
        target.unlink(missing_ok=True)
        raise
    finally:
        origin.close()
        destination.close()

    _apply_retention(backup_dir, keep)
    return target


def _apply_retention(backup_dir, keep):
    """Remove as copias mais antigas; so toca arquivos com o nome do comando."""

    copies = sorted(
        path
        for path in backup_dir.iterdir()
        if path.name.startswith(BACKUP_PREFIX) and path.name.endswith(BACKUP_SUFFIX)
    )
    for old in copies[:-keep]:
        old.unlink()
