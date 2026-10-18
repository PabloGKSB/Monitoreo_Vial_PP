from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from src.central_api import create_central_app
from src.database import CentralStore, database_engine, metadata
from test_api import capture_bytes, await_job


@pytest.fixture
def store(tmp_path):
    engine = database_engine(f"sqlite:///{tmp_path / 'limited.db'}", test_backend=True)
    metadata.create_all(engine)
    yield CentralStore(engine)
    engine.dispose()


def test_quota_is_private_and_rejected_upload_is_removed(store, tmp_path, identities):
    verifier, token, owner_a, owner_b = identities
    app = create_central_app(store, verifier, tmp_path / 'files', max_jobs_24h=1)
    with TestClient(app) as client:
        client.headers['Authorization'] = f'Bearer {token(owner_a)}'
        first = client.post('/v1/jobs', files={'file': ('a.zip', capture_bytes())})
        assert first.status_code == 202
        await_job(client, first.json()['job_id'])
        response = client.post('/v1/jobs', files={'file': ('a.zip', capture_bytes())})
        assert response.status_code == 429
        assert len(list((tmp_path / 'files').iterdir())) == 1
        assert len(client.get('/v1/jobs').json()) == 1
        client.headers['Authorization'] = f'Bearer {token(owner_b)}'
        assert client.post('/v1/jobs', files={'file': ('b.zip', capture_bytes())}).status_code == 202


def test_daily_bytes_and_free_storage_limits(store, tmp_path, identities, monkeypatch):
    verifier, token, *_ = identities
    app = create_central_app(store, verifier, tmp_path / 'files', max_bytes_24h=1)
    with TestClient(app) as client:
        client.headers['Authorization'] = f'Bearer {token()}'
        assert client.post('/v1/jobs', files={'file': ('a.zip', capture_bytes())}).status_code == 429
        assert client.get('/v1/jobs').json() == []
        monkeypatch.setattr('src.central_api.shutil.disk_usage', lambda path: type('Space', (), {'free': 0})())
        assert client.post('/v1/jobs', files={'file': ('a.zip', capture_bytes())}).status_code == 507
        assert not list((tmp_path / 'files').iterdir())


def test_ingress_limits_with_and_without_content_length(store, tmp_path, identities):
    verifier, token, *_ = identities
    app = create_central_app(store, verifier, tmp_path / 'files', max_upload=10)
    with TestClient(app) as client:
        assert client.post('/v1/jobs', content=b'ignored').status_code == 401
        client.headers['Authorization'] = f'Bearer {token()}'
        assert client.post('/v1/jobs', headers={'Content-Length': str(3*1024*1024)}, content=b'x').status_code == 413
        response = client.post('/v1/jobs', content=iter([b'x'*(1024*1024)]*3))
        assert response.status_code == 413
        assert not list((tmp_path / 'files').iterdir())


def test_client_configuration_never_exposes_server_credentials(store, tmp_path, identities, monkeypatch):
    verifier, *_ = identities
    monkeypatch.setenv('VIAL_DATABASE_URL', 'server-only-password')
    app = create_central_app(store, verifier, tmp_path / 'files', publishable_key='sb_publishable_test')
    with TestClient(app) as client:
        response = client.get('/v1/client-config')
        assert response.json() == {'supabase_url':'https://fixture.supabase.co',
                                  'publishable_key':'sb_publishable_test', 'max_upload_bytes':64*1024*1024}
        assert response.headers['Cache-Control'] == 'private, no-store'
        if (Path(__file__).resolve().parent.parent / 'web/dist/index.html').exists():
            assert client.get('/').status_code == 200
            assert "script-src 'self'" in client.get('/').headers['Content-Security-Policy']
    with pytest.raises(ValueError, match='publishable'):
        create_central_app(store, verifier, tmp_path / 'other', publishable_key='sb_secret_rejected')
