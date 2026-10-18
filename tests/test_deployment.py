from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import URL

from src.central_api import create_central_app
from src.deployment import deployment_preflight, public_origin
from test_central_limits import store


@pytest.mark.parametrize('value', ['http://example.com', 'https://user:pass@example.com',
                                  'https://example.com/path', 'https://example.com?secret=x', ''])
def test_invalid_public_origins(value):
    with pytest.raises(ValueError):
        public_origin(value)


def test_public_mode_requires_host_and_https_but_keeps_healthcheck(store, tmp_path, identities):
    verifier, token, *_ = identities
    app = create_central_app(store, verifier, tmp_path/'files', origin='https://vial.example')
    with TestClient(app, base_url='https://vial.example') as client:
        assert client.get('/v1/me', headers={'Authorization':f'Bearer {token()}'}).status_code == 200
        assert client.get('/').headers['Strict-Transport-Security'] == 'max-age=86400'
        assert client.get('/v1/me', headers={'Host':'attacker.example'}).status_code == 400
    with TestClient(app, base_url='http://vial.example') as client:
        assert client.get('/health').status_code == 200
        assert client.get('/v1/me', headers={'Authorization':f'Bearer {token()}'}).status_code == 400


def test_preflight_rejects_unencrypted_upstream_and_ephemeral_storage(tmp_path):
    ca = tmp_path/'root.crt'
    ca.write_text('fixture')
    env = {'VIAL_PUBLIC_ORIGIN':'https://vial.example', 'SUPABASE_PUBLISHABLE_KEY':'sb_publishable_fixture',
           'VIAL_DATABASE_URL':URL.create('postgresql+psycopg', host='db.example',
               query={'sslmode':'verify-full','sslrootcert':str(ca)}).render_as_string(),
           'VIAL_API_STORAGE':str(tmp_path/'archives')}

    class Connection:
        class Driver:
            class PG:
                ssl_in_use = True
            pgconn = PG()
        class Wrapped:
            pass
        connection = Wrapped()
        connection.driver_connection = Driver()

        def execute(self, statement):
            return self

        def one(self):
            return ('vial_backend', False, False, False, False)

        def scalar(self, statement):
            return False

    class Engine:
        @contextmanager
        def connect(self):
            yield Connection()

    with pytest.raises(ValueError, match='volumen persistente'):
        deployment_preflight(env, Engine())
    env.update(VIAL_VOLUME_ROOT=str(tmp_path), VIAL_PERSISTENT_STORAGE_CONFIRMED='1')
    with pytest.raises(ValueError, match='pooler y PostgreSQL'):
        deployment_preflight(env, Engine())
