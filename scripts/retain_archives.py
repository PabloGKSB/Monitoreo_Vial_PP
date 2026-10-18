"""Plan retention by default; --delete-expired removes only eligible originals.

Results/history stay in PostgreSQL. Run while the single API process is stopped.
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
import os
from sqlalchemy import select

from src.database import database_engine, jobs


def eligible_archives(connection, root: Path, days: int):
    if days <= 0:
        raise ValueError('La retencion debe ser positiva')
    root = root.resolve(strict=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    identifiers = connection.scalars(select(jobs.c.id).where(
        jobs.c.created_at < cutoff, jobs.c.status.in_(['COMPLETED', 'FAILED'])))
    for identifier in identifiers:
        directory = root / str(UUID(str(identifier)))
        archive = directory / 'input.zip'
        if directory.is_symlink() or archive.is_symlink():
            raise ValueError('La retencion no sigue enlaces simbolicos')
        if archive.is_file():
            resolved = archive.resolve(strict=True)
            if resolved.parent.parent != root or resolved.name != 'input.zip':
                raise ValueError('Archivo fuera del almacenamiento configurado')
            yield resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--delete-expired', action='store_true')
    args = parser.parse_args()
    load_dotenv(args.env_file, override=False)
    engine = database_engine(os.environ['VIAL_DATABASE_URL'])
    try:
        with engine.connect() as connection:
            candidates = list(eligible_archives(connection, Path(os.environ['VIAL_API_STORAGE']), args.days))
        size = sum(path.stat().st_size for path in candidates)
        if args.delete_expired:
            for path in candidates:
                path.unlink()
        print({'mode':'delete' if args.delete_expired else 'dry-run',
               'archives':len(candidates), 'bytes':size})
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
