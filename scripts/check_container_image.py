"""Offline smoke check inside the image; never uses a production database."""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from threading import Thread
import time
from urllib.error import HTTPError
from urllib.request import urlopen

# The check is bind-mounted at /tmp, while the application lives at /app.
sys.path.insert(0, '/app')

import uvicorn

from src.auth import SupabaseVerifier
from src.central_api import create_central_app
from src.database import CentralStore, database_engine, metadata


def main():
    assert sys.version_info[:2] == (3, 12), 'Expected Python 3.12'
    assert os.getuid() == os.getgid() == 10001, 'Expected unprivileged image user'
    assert shutil.which('node') is None, 'Node must stay in the build stage'
    assert not os.environ.get('VIAL_DATABASE_URL'), 'Production variables are forbidden'
    for private_path in ('.env', '.api_local', 'Data', 'capturas'):
        assert not (Path('/app') / private_path).exists(), 'Private artifacts in image'
    assert Path('/app/web/dist/assets/client.js').is_file(), 'Missing client bundle'
    assert Path('/app/deploy/prod-ca-2021.crt').is_file(), 'Missing public CA'
    checks = {}
    with tempfile.TemporaryDirectory(prefix='vial-image-') as temporary:
        # This explicitly isolated test backend does not exercise PostgreSQL/TLS.
        engine = database_engine('sqlite:///' + str(Path(temporary) / 'test.db'), test_backend=True)
        metadata.create_all(engine)
        application = create_central_app(
            CentralStore(engine), SupabaseVerifier('https://validation.invalid'),
            Path(temporary) / 'archives', publishable_key='sb_publishable_validation')
        server = uvicorn.Server(uvicorn.Config(application, host='127.0.0.1', port=8080,
                                               access_log=False, log_level='warning'))
        thread = Thread(target=server.run, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started:
                assert thread.is_alive(), 'Server exited during startup'
                assert time.monotonic() < deadline, 'Server startup timed out'
                time.sleep(0.05)
            for name, path, expected in (('health', '/health', 200),
                                          ('frontend', '/', 200),
                                          ('unauthenticated', '/v1/me', 401)):
                try:
                    with urlopen('http://127.0.0.1:8080' + path, timeout=5) as response:
                        status = response.status
                        response.read()
                except HTTPError as response:
                    status = response.code
                    response.close()
                assert status == expected, f'{name}: expected {expected}, got {status}'
                checks[name] = status
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            engine.dispose()
        assert not thread.is_alive(), 'Server did not stop'
    print(json.dumps({'checks': checks, 'uid': os.getuid(), 'runtime_node': False,
                      'backend': 'isolated-synthetic-sqlite', 'network': 'none',
                      'production_entrypoint_checked': False, 'production_validated': False}))


if __name__ == '__main__':
    main()
