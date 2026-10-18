import json
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.central_api import app_from_env, create_central_app
from src.database import CentralStore, database_engine, jobs, metadata, observations, trips, users
from test_api import await_job, capture_bytes


@pytest.fixture
def central(tmp_path, identities):
    engine = database_engine(f"sqlite:///{tmp_path / 'central.db'}", test_backend=True)
    metadata.create_all(engine)
    store = CentralStore(engine)
    verifier, token, owner_a, owner_b = identities
    storage = tmp_path / "archives"
    app = create_central_app(store, verifier, storage)
    yield app, store, token, owner_a, owner_b, storage
    engine.dispose()


def upload(client, token, data=None):
    return client.post("/v1/jobs", headers={"Authorization": f"Bearer {token}"},
                       files={"file": ("capture.zip", data or capture_bytes(), "application/zip")})


def test_two_users_have_isolated_jobs_results_maps_and_archives(central):
    app, store, token, owner_a, owner_b, storage = central
    with TestClient(app) as client:
        assert client.get("/health").json()["authentication"] == "supabase_jwt"
        assert client.get("/v1/me").status_code == 401
        assert client.get("/v1/jobs").status_code == 401
        assert client.post("/v1/jobs",files={"file":("x.zip",capture_bytes())}).status_code == 401
        client.headers["Authorization"] = f"Bearer {token(owner_a)}"
        assert client.get("/v1/me").json()["user_id"] == str(owner_a)
        data = capture_bytes()
        response = upload(client,token(owner_a),data)
        assert response.status_code == 202
        job_a = response.json()["job_id"]
        assert await_job(client,job_a)["status"] == "COMPLETED"
        assert len(client.get("/v1/jobs").json()) == 1
        result = client.get(f"/v1/jobs/{job_a}/result").json()
        assert result["detection"]["event_count"] is None
        assert not result["processing_policy"]["detection_allowed"]
        assert client.get(f"/v1/jobs/{job_a}/archive").content == data
        assert client.get(f"/v1/jobs/{job_a}/result").headers["Cache-Control"] == "private, no-store"
        assert client.get(f"/v1/jobs/{job_a}/map").headers["Referrer-Policy"] == "no-referrer"
        assert client.get(f"/v1/jobs/{job_a}/map").text.count("L.polyline(") == 2
        client.headers["Authorization"] = f"Bearer {token(owner_b)}"
        assert client.get("/v1/jobs").json() == []
        for suffix in ("", "/result", "/map", "/archive"):
            assert client.get(f"/v1/jobs/{job_a}{suffix}").status_code == 404
        response_b = upload(client,token(owner_b))
        job_b = response_b.json()["job_id"]
        assert await_job(client,job_b)["status"] == "COMPLETED"
        assert [row["job_id"] for row in client.get("/v1/jobs").json()] == [job_b]
        assert client.get("/v1/jobs?limit=101").status_code == 422
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token(owner_a)}"
        assert client.get(f"/v1/jobs/{job_a}/result").status_code == 200
        assert client.get(f"/v1/jobs/{job_b}").status_code == 404
    assert len(list(storage.glob("*/input.zip"))) == 2
    with store.engine.connect() as connection:
        assert len(connection.execute(select(trips)).all()) == 2
        assert connection.execute(select(observations)).all() == []


def test_container_rejection_cleanup_and_invalid_profile(central):
    app, store, token, owner_a, _, storage = central
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token()}"
        bad = upload(client,token(),b"invalid zip")
        assert bad.status_code == 422
        assert not list(storage.iterdir())
        assert client.get("/v1/jobs").json() == []
        job_id = upload(client,token(),capture_bytes(version="future")).json()["job_id"]
        record = await_job(client,job_id)
        assert record["status"] == "FAILED"
        assert record["error"]["code"] == "INVALID_TRIP"
        assert client.get(f"/v1/jobs/{job_id}/result").status_code == 409


def test_central_recovery_of_interrupted_work(central):
    app, store, token, owner_a, _, _ = central
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token()}"
        job_id = upload(client,token()).json()["job_id"]
        record = await_job(client,job_id)
    with store.engine.begin() as connection:
        connection.execute(jobs.update().where(jobs.c.id==UUID(job_id)).values(status="PROCESSING"))
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token()}"
        recovered = client.get(f"/v1/jobs/{job_id}").json()
        assert recovered["status"] == "FAILED"
        assert recovered["error"]["code"] == "PROCESS_INTERRUPTED"


def test_database_rejects_trip_links_across_owners(central):
    app, store, token, owner_a, owner_b, _ = central
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token()}"
        job_id = upload(client,token()).json()["job_id"]
        await_job(client,job_id)
    with store.engine.begin() as connection:
        trip_id = connection.scalar(select(jobs.c.trip_id).where(jobs.c.id==UUID(job_id)))
        connection.execute(users.insert().values(id=owner_b,issuer="https://fixture.supabase.co/auth/v1"))
    with pytest.raises(IntegrityError), store.engine.begin() as connection:
        connection.execute(observations.insert().values(id=uuid4(),owner_id=owner_b,trip_id=trip_id,
                                                        event_type="BACHE",latitude=-38.7,longitude=-72.6))
    with pytest.raises(IntegrityError), store.engine.begin() as connection:
        connection.execute(observations.insert().values(id=uuid4(),owner_id=owner_a,trip_id=trip_id,
                                                        event_type="BACHE",latitude=100,longitude=-72.6))


def test_central_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL",raising=False)
    monkeypatch.delenv("VIAL_DATABASE_URL",raising=False)
    with pytest.raises(RuntimeError,match="no se habilita acceso anonimo"):
        app_from_env()
    with pytest.raises(ValueError,match="PostgreSQL"):
        database_engine("sqlite:///not-permitted.db")
