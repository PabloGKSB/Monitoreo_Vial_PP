"""Opt-in migration/spatial test: only point this at a disposable test database."""

from datetime import datetime, timezone
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text

from src.auth import Identity
from src.database import CentralStore, database_engine, observations


@pytest.mark.skipif(not os.environ.get("VIAL_TEST_DATABASE_URL"), reason="No hay PostgreSQL/PostGIS de pruebas configurado")
def test_migrations_records_and_spatial_point(monkeypatch):
    monkeypatch.setenv("VIAL_DATABASE_URL", os.environ["VIAL_TEST_DATABASE_URL"])
    command.upgrade(Config("alembic.ini"), "head")
    engine = database_engine(os.environ["VIAL_TEST_DATABASE_URL"])
    try:
        store = CentralStore(engine)
        store.check_schema()
        owner, other, job_id = uuid4(), uuid4(), uuid4()
        now = datetime.now(timezone.utc).isoformat()
        record = {"job_id":str(job_id),"status":"QUEUED","created_at":now,"updated_at":now,
                  "filename":"synthetic.zip","upload_bytes":1,"sha256":"0"*64}
        store.create_job(Identity(owner,"https://synthetic.supabase.co/auth/v1"),record)
        store.mark_processing(job_id,owner)
        store.complete(job_id,owner,{"trip_id":"synthetic","capture_profile":"sensor-logger-legacy",
                                     "quality":{"overall_status":"WARNING"}})
        assert store.get_job(job_id,other) is None
        assert store.get_job(job_id,owner)["status"] == "COMPLETED"
        with engine.begin() as connection:
            trip_id = connection.scalar(text("SELECT trip_id FROM vial.jobs WHERE id=:id"),{"id":job_id})
            point_id = uuid4()
            connection.execute(observations.insert().values(id=point_id,owner_id=owner,trip_id=trip_id,
                                event_type="OTRO",latitude=0,longitude=0))
            schema = connection.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='postgis'"))
            quoted = connection.dialect.identifier_preparer.quote_schema(schema)
            srid = connection.scalar(text(f"SELECT {quoted}.ST_SRID(geom) FROM vial.observations WHERE id=:id"),{"id":point_id})
            assert srid == 4326
            assert connection.scalar(text("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='vial' AND c.relname IN ('users','trips','jobs','observations') AND c.relrowsecurity")) == 4
    finally:
        engine.dispose()
