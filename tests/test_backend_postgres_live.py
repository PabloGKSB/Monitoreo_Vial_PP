"""Opt-in runtime checks against an already migrated database.

Synthetic application records stay inside a transaction that is rolled back.
These checks never migrate the database or create Supabase Auth accounts.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.auth import Identity
from src.database import CentralStore, database_engine


pytestmark = pytest.mark.skipif(
    not os.environ.get("VIAL_RUNTIME_TEST_DATABASE_URL"),
    reason="No hay conexion optativa con el rol backend configurada",
)


@pytest.fixture
def runtime_connection():
    engine = database_engine(os.environ["VIAL_RUNTIME_TEST_DATABASE_URL"])
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                role = connection.execute(text(
                    "SELECT current_user, rolbypassrls, rolsuper, rolcreaterole, rolcreatedb "
                    "FROM pg_roles WHERE rolname=current_user"
                )).one()
                assert tuple(role) == ("vial_backend", False, False, False, False)
                assert connection.connection.driver_connection.pgconn.ssl_in_use
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_runtime_store_lifecycle_and_owner_isolation(runtime_connection):
    connection = runtime_connection

    class TransactionEngine:
        dialect = connection.dialect

        @contextmanager
        def connect(self):
            yield connection

        @contextmanager
        def begin(self):
            with connection.begin_nested():
                yield connection

    store = CentralStore(TransactionEngine())
    store.check_schema()
    owner, other, job_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc).isoformat()
    record = {"job_id": str(job_id), "status": "QUEUED", "created_at": now,
              "updated_at": now, "filename": "runtime-check.zip", "upload_bytes": 1,
              "sha256": "0" * 64}
    identity = Identity(owner, "https://runtime-check.invalid/auth/v1")
    store.create_job(identity, record)
    assert store.get_job(job_id, other) is None
    assert store.list_jobs(other, 20, 0) == []
    assert store.get_job(job_id, owner)["status"] == "QUEUED"
    store.mark_processing(job_id, owner)
    result = {"trip_id": "runtime-check", "capture_profile": "sensor-logger-legacy",
              "quality": {"overall_status": "WARNING"}}
    store.complete(job_id, owner, result)
    assert store.get_job(job_id, owner)["status"] == "COMPLETED"
    assert store.get_result(job_id, owner) == result
    assert store.get_result(job_id, other) is None
    assert len(store.list_jobs(owner, 20, 0)) == 1

    failed_id = uuid4()
    store.create_job(identity, {**record, "job_id": str(failed_id)})
    store.fail(failed_id, owner, {"code": "RUNTIME_CHECK"})
    assert store.get_job(failed_id, owner)["error"]["code"] == "RUNTIME_CHECK"


@pytest.mark.parametrize("statement", [
    "SELECT * FROM auth.users LIMIT 0",
    "SELECT * FROM public.alembic_version LIMIT 0",
    "DELETE FROM vial.jobs WHERE false",
    "UPDATE vial.jobs SET owner_id=owner_id WHERE false",
    "INSERT INTO vial.observations DEFAULT VALUES",
    "CREATE TABLE vial.runtime_check_forbidden (id integer)",
])
def test_runtime_rejects_unneeded_privileges(runtime_connection, statement):
    with pytest.raises(DBAPIError) as error:
        with runtime_connection.begin_nested():
            runtime_connection.execute(text(statement))
    assert error.value.orig.sqlstate == "42501"
