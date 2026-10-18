from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from scripts.restore_application import inspect_snapshot, restore
from src.database import database_engine, metadata, users, trips, jobs, observations


@pytest.fixture
def target_engine(tmp_path):
    engine = database_engine('sqlite:///' + str(tmp_path / 'restore.db'), test_backend=True)
    metadata.create_all(engine)
    yield engine
    engine.dispose()


def snapshot(tmp_path, mutate=None, extra=None):
    owner, trip, job, observation = (str(uuid4()) for _ in range(4))
    original = b'synthetic private archive'
    digest = sha256(original).hexdigest()
    now = '2026-10-18T12:34:56.123456+00:00'
    rows = {
        'users': [{'id': owner, 'issuer': 'https://restore.invalid/auth/v1'}],
        'trips': [{'id': trip, 'owner_id': owner, 'source_trip_id': 'synthetic',
                   'capture_profile': 'sensor-logger-legacy', 'quality_status': 'OK', 'created_at': now}],
        'jobs': [{'id': job, 'owner_id': owner, 'trip_id': trip, 'status': 'COMPLETED',
                  'created_at': now, 'updated_at': now, 'filename': 'synthetic.zip',
                  'upload_bytes': len(original), 'sha256': digest, 'error': None,
                  'result': {'quality': {'overall_status': 'OK'}, 'values': [1, None, 'señal']}}],
        'observations': [{'id': observation, 'owner_id': owner, 'trip_id': trip, 'event_type': 'OTRO',
                          'latitude': 0.125, 'longitude': -0.25, 'review_status': 'PENDING'}],
    }
    manifest = {'version': 'vial-backup-1', 'schema_revision': '0002_backend_role',
                'counts': {name: len(records) for name, records in rows.items()},
                'originals': {job: digest}, 'missing_originals': []}
    contents = {'records.json': rows, 'manifest.json': manifest,
                'archives/' + job + '/input.zip': original}
    if mutate:
        mutate(rows, manifest, contents)
    path = tmp_path / ('snapshot-' + uuid4().hex + '.zip')
    with ZipFile(path, 'x', compression=ZIP_DEFLATED) as archive:
        for name, value in contents.items():
            archive.writestr(name, value if isinstance(value, bytes) else json.dumps(value))
        if extra:
            archive.writestr(extra, 'unexpected')
    return path, rows, original


def test_restore_preserves_ids_dates_json_and_originals(target_engine, tmp_path):
    path, rows, original = snapshot(tmp_path)
    target = tmp_path / 'restored'
    result = restore(target_engine, path, target)
    assert result['counts'] == dict.fromkeys(('users', 'trips', 'jobs', 'observations'), 1)
    assert result['auth_restored'] is False
    with target_engine.connect() as connection:
        job = connection.execute(select(jobs)).mappings().one()
        assert str(job['id']) == rows['jobs'][0]['id']
        assert job['created_at'].replace(tzinfo=timezone.utc) == datetime.fromisoformat(rows['jobs'][0]['created_at'])
        assert job['result'] == rows['jobs'][0]['result']
        assert job['error'] is None
        assert connection.scalar(select(func.count()).select_from(observations)) == 1
    assert (target / rows['jobs'][0]['id'] / 'input.zip').read_bytes() == original


@pytest.mark.parametrize('kind', ['hash', 'size', 'missing', 'pending', 'count', 'generated-column', 'date'])
def test_invalid_snapshot_never_writes_target(target_engine, tmp_path, kind):
    def mutate(rows, manifest, contents):
        if kind == 'hash': rows['jobs'][0]['sha256'] = '0' * 64
        elif kind == 'size': rows['jobs'][0]['upload_bytes'] += 1
        elif kind == 'missing': manifest['missing_originals'] = [rows['jobs'][0]['id']]
        elif kind == 'pending': rows['jobs'][0]['status'] = 'PROCESSING'
        elif kind == 'count': manifest['counts']['jobs'] += 1
        elif kind == 'generated-column': rows['observations'][0]['geom'] = 'forbidden'
        elif kind == 'date': rows['jobs'][0]['created_at'] = '2026-10-18T12:00:00'
    path, _, _ = snapshot(tmp_path, mutate)
    target = tmp_path / 'refused'
    with pytest.raises(ValueError):
        restore(target_engine, path, target)
    assert not target.exists()
    with target_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(users)) == 0


@pytest.mark.parametrize('extra', ['../escape', '/absolute', 'archives/not-a-uuid/input.zip', 'records.json'])
def test_unexpected_paths_and_duplicates_are_rejected(tmp_path, extra):
    path, _, _ = snapshot(tmp_path, extra=extra)
    with pytest.raises(ValueError):
        inspect_snapshot(path)
    assert not (tmp_path.parent / 'escape').exists()


def test_nonempty_database_and_existing_directory_are_preserved(target_engine, tmp_path):
    path, _, _ = snapshot(tmp_path)
    existing = tmp_path / 'existing'
    existing.mkdir()
    sentinel = existing / 'keep'
    sentinel.write_text('untouched')
    with pytest.raises(ValueError, match='directorio destino'):
        restore(target_engine, path, existing)
    assert sentinel.read_text() == 'untouched'
    with target_engine.begin() as connection:
        connection.execute(users.insert().values(id=uuid4(), issuer='https://existing.invalid'))
    with pytest.raises(ValueError, match='base destino debe estar vacia'):
        restore(target_engine, path, tmp_path / 'new')
    with target_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(users)) == 1


def test_foreign_key_failure_rolls_back_rows_and_owned_files(target_engine, tmp_path):
    def mutate(rows, manifest, contents):
        rows['observations'][0]['owner_id'] = str(uuid4())
    path, _, _ = snapshot(tmp_path, mutate)
    target = tmp_path / 'rollback'
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        restore(target_engine, path, target)
    assert not target.exists()
    with target_engine.connect() as connection:
        assert all(connection.scalar(select(func.count()).select_from(table)) == 0
                   for table in (users, trips, jobs, observations))


def test_active_postgres_database_name_is_rejected_before_connecting(tmp_path):
    engine = SimpleNamespace(dialect=SimpleNamespace(name='postgresql'),
                             url=SimpleNamespace(database='postgres'))
    with pytest.raises(ValueError, match='vial_restore_'):
        restore(engine, tmp_path/'not-opened.zip', tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()
