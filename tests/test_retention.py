from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from scripts.retain_archives import eligible_archives
from src.database import jobs, users
from test_central_limits import store


def test_retention_selects_only_expired_finished_archives(store, tmp_path):
    root = tmp_path/'archives'
    root.mkdir()
    owner = uuid4()
    now = datetime.now(timezone.utc)
    selected = []
    with store.engine.begin() as connection:
        connection.execute(users.insert().values(id=owner, issuer='https://retention.invalid/auth/v1'))
        for status, days in [('COMPLETED',31),('FAILED',31),('PROCESSING',31),('COMPLETED',1)]:
            identifier = uuid4()
            connection.execute(jobs.insert().values(id=identifier, owner_id=owner,
                status=status, created_at=now-timedelta(days=days), updated_at=now,
                filename='test.zip', upload_bytes=4, sha256='0'*64))
            directory = root/str(identifier)
            directory.mkdir()
            archive = directory/'input.zip'
            archive.write_bytes(b'test')
            (directory/'keep.txt').write_text('keep')
            if status in {'COMPLETED','FAILED'} and days>30:
                selected.append(archive)
    with store.engine.connect() as connection:
        planned = list(eligible_archives(connection,root,30))
    assert set(planned) == set(selected)
    assert all(path.read_bytes()==b'test' for path in planned)  # Planning never deletes.
    assert len(list(root.glob('*/keep.txt'))) == 4
    with store.engine.connect() as connection, pytest.raises(ValueError):
        list(eligible_archives(connection,root,0))
