from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import select, func

from scripts.backup_central import backup
from src.database import users, jobs
from test_central_limits import store


@pytest.mark.parametrize('corrupt',[False, True])
def test_application_backup_is_read_only_and_checks_original_hashes(store, tmp_path, corrupt):
    root = tmp_path/'archives'
    root.mkdir()
    owner, identifier = uuid4(), uuid4()
    payload = b'private original fixture'
    directory = root/str(identifier)
    directory.mkdir()
    (directory/'input.zip').write_bytes(b'changed' if corrupt else payload)
    now = datetime.now(timezone.utc)
    with store.engine.begin() as connection:
        connection.execute(users.insert().values(id=owner,issuer='https://backup.invalid/auth/v1'))
        connection.execute(jobs.insert().values(id=identifier,owner_id=owner,status='FAILED',
            created_at=now,updated_at=now,filename='fixture.zip',upload_bytes=len(payload),
            sha256=sha256(payload).hexdigest()))
    destination = tmp_path/'snapshot.zip'
    if corrupt:
        with pytest.raises(ValueError,match='hash registrado'):
            backup(store.engine,root,destination)
    else:
        manifest = backup(store.engine,root,destination)
        assert manifest['counts']['jobs'] == 1
        with ZipFile(destination) as archive:
            assert archive.read('archives/'+str(identifier)+'/input.zip') == payload
            records = json.loads(archive.read('records.json'))
            assert set(records['users'][0]) == {'id','issuer'}
            assert 'auth' not in records
    with store.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(jobs)) == 1
    assert (directory/'input.zip').is_file()
