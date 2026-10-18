"""Central relational store; PostgreSQL is required outside isolated tests."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import (CheckConstraint, Column, DateTime, Float, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, JSON, MetaData,
                        String, Table, UniqueConstraint, Uuid, create_engine, event, func, select, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from .auth import Identity

metadata = MetaData(schema="vial")
json_type = JSON().with_variant(JSONB(), "postgresql")
users = Table("users", metadata,
              Column("id", Uuid, primary_key=True), Column("issuer", String(512), nullable=False))
trips = Table("trips", metadata,
              Column("id", Uuid, primary_key=True),
              Column("owner_id", Uuid, ForeignKey("vial.users.id"), nullable=False),
              Column("source_trip_id", String(512), nullable=False),
              Column("capture_profile", String(64), nullable=False),
              Column("quality_status", String(16), nullable=False),
              Column("created_at", DateTime(timezone=True), nullable=False),
              UniqueConstraint("id", "owner_id", name="uq_trip_owner"),
              CheckConstraint("quality_status IN ('OK','WARNING','INVALID')", name="ck_trip_quality"))
jobs = Table("jobs", metadata,
             Column("id", Uuid, primary_key=True),
             Column("owner_id", Uuid, ForeignKey("vial.users.id"), nullable=False),
             Column("trip_id", Uuid, nullable=True),
             Column("status", String(16), nullable=False),
             Column("created_at", DateTime(timezone=True), nullable=False),
             Column("updated_at", DateTime(timezone=True), nullable=False),
             Column("filename", String(200), nullable=False),
             Column("upload_bytes", Integer, nullable=False),
             Column("sha256", String(64), nullable=False),
             Column("error", json_type), Column("result", json_type),
             ForeignKeyConstraint(["trip_id", "owner_id"], ["vial.trips.id", "vial.trips.owner_id"], name="fk_job_trip_owner"),
             CheckConstraint("status IN ('QUEUED','PROCESSING','COMPLETED','FAILED')", name="ck_job_status"),
             CheckConstraint("upload_bytes >= 0", name="ck_job_size"))
observations = Table("observations", metadata,
                     Column("id", Uuid, primary_key=True),
                     Column("owner_id", Uuid, ForeignKey("vial.users.id"), nullable=False),
                     Column("trip_id", Uuid, nullable=False), Column("event_type", String(64), nullable=False),
                     Column("latitude", Float, nullable=False), Column("longitude", Float, nullable=False),
                     Column("review_status", String(16), nullable=False, server_default="PENDING"),
                     ForeignKeyConstraint(["trip_id", "owner_id"], ["vial.trips.id", "vial.trips.owner_id"], name="fk_observation_trip_owner"),
                     CheckConstraint("latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180", name="ck_observation_coordinates"),
                     CheckConstraint("review_status IN ('PENDING','CONFIRMED','REJECTED')", name="ck_observation_review"))
Index("ix_jobs_owner_created", jobs.c.owner_id, jobs.c.created_at)
Index("ix_trips_owner_created", trips.c.owner_id, trips.c.created_at)


def database_engine(url: str, *, test_backend=False) -> Engine:
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite") and test_backend:
        engine = create_engine(url, connect_args={"check_same_thread": False},
                               execution_options={"schema_translate_map": {"vial": None}})

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        return engine
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("El modo central requiere PostgreSQL; SQLite solo esta habilitado en pruebas")
    return create_engine(url, pool_pre_ping=True)


class UploadQuotaExceeded(Exception):
    pass


class CentralStore:
    def __init__(self, engine: Engine):
        self.engine = engine

    def check_schema(self):
        with self.engine.connect() as connection:
            connection.execute(select(jobs).limit(0))
            if self.engine.dialect.name == "postgresql":
                from sqlalchemy import text
                connection.execute(text("SELECT geom FROM vial.observations LIMIT 0"))

    def create_job(self, identity: Identity, record: dict, *, max_jobs_24h=None, max_bytes_24h=None):
        with self.engine.begin() as connection:
            if (max_jobs_24h is not None or max_bytes_24h is not None) and self.engine.dialect.name == "postgresql":
                # Serialize quota checks for this owner without granting UPDATE on users.
                connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:owner, 0))"),
                                   {"owner": str(identity.user_id)})
            if max_jobs_24h is not None or max_bytes_24h is not None:
                count, size = connection.execute(select(func.count(), func.coalesce(func.sum(jobs.c.upload_bytes), 0))
                    .where(jobs.c.owner_id == identity.user_id,
                           jobs.c.created_at >= datetime.now(timezone.utc) - timedelta(hours=24))).one()
                if ((max_jobs_24h is not None and count >= max_jobs_24h)
                        or (max_bytes_24h is not None and size + record["upload_bytes"] > max_bytes_24h)):
                    raise UploadQuotaExceeded("Cupo de cargas de las ultimas 24 horas alcanzado")
            # Savepoint handles simultaneous first requests from the same account.
            from sqlalchemy.exc import IntegrityError
            try:
                with connection.begin_nested():
                    connection.execute(users.insert().values(id=identity.user_id, issuer=identity.issuer))
            except IntegrityError:
                pass
            issuer = connection.scalar(select(users.c.issuer).where(users.c.id == identity.user_id))
            if issuer != identity.issuer:
                raise ValueError("Identity issuer mismatch")
            connection.execute(jobs.insert().values(
                id=UUID(record["job_id"]), owner_id=identity.user_id, status=record["status"],
                created_at=datetime.fromisoformat(record["created_at"]),
                updated_at=datetime.fromisoformat(record["updated_at"]), filename=record["filename"],
                upload_bytes=record["upload_bytes"], sha256=record["sha256"]))

    @staticmethod
    def view(row) -> dict:
        def utc_text(value):
            return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()
        return {"job_id": str(row["id"]), "status": row["status"],
                "created_at": utc_text(row["created_at"]), "updated_at": utc_text(row["updated_at"]),
                "filename": row["filename"], "upload_bytes": row["upload_bytes"],
                "sha256": row["sha256"], "error": row["error"]}

    def get_job(self, job_id: UUID, owner_id: UUID) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.owner_id == owner_id)).mappings().first()
            return self.view(row) if row else None

    def list_jobs(self, owner_id: UUID, limit: int, offset: int) -> list[dict]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(jobs).where(jobs.c.owner_id == owner_id)
                                      .order_by(jobs.c.created_at.desc(), jobs.c.id).limit(limit).offset(offset)).mappings()
            return [self.view(row) for row in rows]

    def get_result(self, job_id: UUID, owner_id: UUID) -> dict | None:
        with self.engine.connect() as connection:
            return connection.scalar(select(jobs.c.result).where(jobs.c.id == job_id, jobs.c.owner_id == owner_id))

    def mark_processing(self, job_id: UUID, owner_id: UUID):
        with self.engine.begin() as connection:
            connection.execute(jobs.update().where(jobs.c.id == job_id, jobs.c.owner_id == owner_id,
                                                   jobs.c.status == "QUEUED").values(
                status="PROCESSING", updated_at=datetime.now(timezone.utc)))

    def complete(self, job_id: UUID, owner_id: UUID, result: dict):
        with self.engine.begin() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.owner_id == owner_id,
                                                       jobs.c.status == "PROCESSING")).mappings().first()
            if row is None:
                raise ValueError("Job not processing for this owner")
            trip_id = uuid4()
            connection.execute(trips.insert().values(id=trip_id, owner_id=owner_id,
                source_trip_id=result["trip_id"], capture_profile=result["capture_profile"],
                quality_status=result["quality"]["overall_status"], created_at=datetime.now(timezone.utc)))
            connection.execute(jobs.update().where(jobs.c.id == job_id, jobs.c.owner_id == owner_id).values(
                trip_id=trip_id, status="COMPLETED", result=result, updated_at=datetime.now(timezone.utc), error=None))

    def fail(self, job_id: UUID, owner_id: UUID, error: dict):
        with self.engine.begin() as connection:
            connection.execute(jobs.update().where(jobs.c.id == job_id, jobs.c.owner_id == owner_id,
                                                   jobs.c.status.in_(["QUEUED", "PROCESSING"])).values(
                status="FAILED", error=error, updated_at=datetime.now(timezone.utc)))

    def interrupt_pending(self):
        # Only a single process may own the worker in this increment.
        with self.engine.begin() as connection:
            connection.execute(jobs.update().where(jobs.c.status.in_(["QUEUED", "PROCESSING"])).values(
                status="FAILED", updated_at=datetime.now(timezone.utc), error={
                    "code": "PROCESS_INTERRUPTED", "message": "Trabajo interrumpido; volver a cargar el ZIP"}))
