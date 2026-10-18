"""Synthetic recovery exercise on two explicitly disposable local PostGIS servers.

Never loads .env or Supabase credentials. The two servers must be distinct,
loopback-only, with empty vial_restore_* databases. Run in CI, not production.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4
from zipfile import ZipFile

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from scripts.backup_central import backup, json_value
from scripts.restore_application import restore, TABLES
from src.auth import Identity
from src.database import CentralStore, database_engine, users, trips, jobs, observations


def disposable_url(variable):
    url = make_url(os.environ[variable])
    if (url.host not in {'127.0.0.1', 'localhost'} or not url.port
            or not (url.database or '').startswith('vial_restore_')):
        raise ValueError('Usar solo servidores locales y bases vial_restore_* descartables')
    return url


def migrate_empty(url):
    engine = database_engine(url.render_as_string(hide_password=False))
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT to_regnamespace('vial') IS NOT NULL")):
                raise ValueError('La base descartable ya contiene el esquema vial')
    finally:
        engine.dispose()
    previous = os.environ.get('VIAL_MIGRATION_DATABASE_URL')
    os.environ['VIAL_MIGRATION_DATABASE_URL'] = url.render_as_string(hide_password=False)
    try:
        command.upgrade(Config('alembic.ini'), 'head')
    finally:
        if previous is None:
            os.environ.pop('VIAL_MIGRATION_DATABASE_URL', None)
        else:
            os.environ['VIAL_MIGRATION_DATABASE_URL'] = previous


def normalized_records(engine):
    with engine.connect() as connection:
        return json.loads(json.dumps({table.name: [dict(row) for row in
            connection.execute(select(table).order_by(table.c.id)).mappings()]
            for table in TABLES}, default=json_value))


def main():
    source_url = disposable_url('VIAL_RECOVERY_SOURCE_DATABASE_URL')
    target_url = disposable_url('VIAL_RECOVERY_TARGET_DATABASE_URL')
    if source_url.host == target_url.host and source_url.port == target_url.port:
        raise ValueError('Usar dos servidores descartables distintos para aislar roles')
    migrate_empty(source_url)
    migrate_empty(target_url)
    source = database_engine(source_url.render_as_string(hide_password=False))
    target = database_engine(target_url.render_as_string(hide_password=False))
    identities, identifiers, digests = [], [], []
    try:
        with tempfile.TemporaryDirectory(prefix='vial-recovery-') as temporary:
            root = Path(temporary)
            originals = root / 'source'
            originals.mkdir()
            now = datetime(2026, 10, 18, 12, 34, 56, 123456, tzinfo=timezone.utc)
            with source.begin() as connection:
                for number in range(2):
                    owner, trip, job, observation = (uuid4() for _ in range(4))
                    identity = Identity(owner, 'https://recovery.invalid/auth/v1')
                    identities.append(identity)
                    identifiers.append(job)
                    directory = originals / str(job)
                    directory.mkdir()
                    archive = directory / 'input.zip'
                    with ZipFile(archive, 'x') as output:
                        output.writestr('synthetic.txt', 'Synthetic recovery fixture ' + str(number))
                    digest = sha256(archive.read_bytes()).hexdigest()
                    digests.append(digest)
                    connection.execute(users.insert().values(id=owner, issuer=identity.issuer))
                    connection.execute(trips.insert().values(id=trip, owner_id=owner,
                        source_trip_id='synthetic-' + str(number), capture_profile='sensor-logger-legacy',
                        quality_status='OK', created_at=now))
                    connection.execute(jobs.insert().values(id=job, owner_id=owner, trip_id=trip,
                        status='COMPLETED', created_at=now, updated_at=now,
                        filename='synthetic.zip', upload_bytes=archive.stat().st_size, sha256=digest,
                        error=None, result={'quality': {'overall_status': 'OK'}, 'nested': [None, number, 'señal']}))
                    connection.execute(observations.insert().values(id=observation, owner_id=owner,
                        trip_id=trip, event_type='OTRO', latitude=0.125 + number,
                        longitude=-0.25 - number, review_status='PENDING'))
            snapshot = root / 'snapshot.zip'
            backup(source, originals, snapshot)
            destination = root / 'restored'
            report = restore(target, snapshot, destination)
            assert normalized_records(source) == normalized_records(target), 'Rows differ after recovery'
            with target.connect() as connection:
                extension = connection.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='postgis'"))
                schema = connection.dialect.identifier_preparer.quote_schema(extension)
                valid = connection.scalar(text(f'SELECT count(*) FROM vial.observations WHERE '
                    f'{schema}.ST_SRID(geom)=4326 AND {schema}.ST_X(geom)=longitude '
                    f'AND {schema}.ST_Y(geom)=latitude'))
                assert valid == 2, 'Generated geometry or SRID incorrect'
            # Reconnect with the migrated restricted backend role, not the admin.
            # This fixture password exists only in the disposable local CI target.
            with target.begin() as connection:
                connection.exec_driver_sql("ALTER ROLE vial_backend LOGIN PASSWORD 'recovery-fixture-only'")
            backend_url = target_url.set(username='vial_backend', password='recovery-fixture-only')
            for _ in range(2):
                backend = database_engine(backend_url.render_as_string(hide_password=False))
                try:
                    store = CentralStore(backend)
                    store.check_schema()
                    for index, identity in enumerate(identities):
                        assert len(store.list_jobs(identity.user_id, 20, 0)) == 1
                        assert store.get_job(identifiers[index], identities[1-index].user_id) is None
                        assert store.get_result(identifiers[index], identity.user_id)['nested'][1] == index
                        original = destination / str(identifiers[index]) / 'input.zip'
                        assert sha256(original.read_bytes()).hexdigest() == digests[index]
                finally:
                    backend.dispose()
            print(json.dumps({**report, 'postgres_postgis_checked': True,
                'generated_geometry_srid': 4326, 'uuid_dates_json_preserved': True,
                'owner_isolation_checked': True, 'backend_reconnection_checked': True,
                'production_database_used': False, 'auth_restored': False,
                'external_backup_checked': False, 'railway_volume_checked': False}))
    finally:
        source.dispose()
        target.dispose()


if __name__ == '__main__':
    main()
