"""Private sessions, jobs and candidate observations with PostGIS."""

from alembic import op
from sqlalchemy import text
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_central"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS vial")
    op.execute("CREATE SCHEMA IF NOT EXISTS gis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA gis")
    extension_schema = connection.scalar(text(
        "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='postgis'"))
    schema = connection.dialect.identifier_preparer.quote_schema(extension_schema)
    # Freeze this revision instead of importing models that can change later.
    op.create_table("users", sa.Column("id",sa.Uuid,primary_key=True),
                    sa.Column("issuer",sa.String(512),nullable=False), schema="vial")
    op.create_table("trips", sa.Column("id",sa.Uuid,primary_key=True),
        sa.Column("owner_id",sa.Uuid,sa.ForeignKey("vial.users.id"),nullable=False),
        sa.Column("source_trip_id",sa.String(512),nullable=False),
        sa.Column("capture_profile",sa.String(64),nullable=False),
        sa.Column("quality_status",sa.String(16),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("id","owner_id",name="uq_trip_owner"),
        sa.CheckConstraint("quality_status IN ('OK','WARNING','INVALID')",name="ck_trip_quality"),schema="vial")
    op.create_table("jobs", sa.Column("id",sa.Uuid,primary_key=True),
        sa.Column("owner_id",sa.Uuid,sa.ForeignKey("vial.users.id"),nullable=False),
        sa.Column("trip_id",sa.Uuid), sa.Column("status",sa.String(16),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("filename",sa.String(200),nullable=False), sa.Column("upload_bytes",sa.Integer,nullable=False),
        sa.Column("sha256",sa.String(64),nullable=False), sa.Column("error",JSONB),sa.Column("result",JSONB),
        sa.ForeignKeyConstraint(["trip_id","owner_id"],["vial.trips.id","vial.trips.owner_id"],name="fk_job_trip_owner"),
        sa.CheckConstraint("status IN ('QUEUED','PROCESSING','COMPLETED','FAILED')",name="ck_job_status"),
        sa.CheckConstraint("upload_bytes >= 0",name="ck_job_size"),schema="vial")
    op.create_table("observations", sa.Column("id",sa.Uuid,primary_key=True),
        sa.Column("owner_id",sa.Uuid,sa.ForeignKey("vial.users.id"),nullable=False),
        sa.Column("trip_id",sa.Uuid,nullable=False), sa.Column("event_type",sa.String(64),nullable=False),
        sa.Column("latitude",sa.Float,nullable=False), sa.Column("longitude",sa.Float,nullable=False),
        sa.Column("review_status",sa.String(16),nullable=False,server_default="PENDING"),
        sa.ForeignKeyConstraint(["trip_id","owner_id"],["vial.trips.id","vial.trips.owner_id"],name="fk_observation_trip_owner"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",name="ck_observation_coordinates"),
        sa.CheckConstraint("review_status IN ('PENDING','CONFIRMED','REJECTED')",name="ck_observation_review"),schema="vial")
    op.create_index("ix_jobs_owner_created","jobs",["owner_id","created_at"],schema="vial")
    op.create_index("ix_trips_owner_created","trips",["owner_id","created_at"],schema="vial")
    op.execute(f"""ALTER TABLE vial.observations ADD COLUMN geom {schema}.geometry(Point,4326)
        GENERATED ALWAYS AS ({schema}.ST_SetSRID({schema}.ST_MakePoint(longitude,latitude),4326)) STORED""")
    op.execute("CREATE INDEX ix_observations_geom ON vial.observations USING GIST (geom)")
    # No anonymous Data API access; API checks ownership even if its DB role bypasses RLS.
    for table in ("users", "trips", "jobs", "observations"):
        op.execute(f"ALTER TABLE vial.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON vial.{table} FROM PUBLIC")
    if connection.scalar(text("SELECT to_regprocedure('auth.uid()') IS NOT NULL")):
        for table in ("users", "trips", "jobs", "observations"):
            owner = "id" if table == "users" else "owner_id"
            op.execute(f"CREATE POLICY owner_select ON vial.{table} FOR SELECT TO authenticated USING ({owner} = (SELECT auth.uid()))")


def downgrade():
    # An explicit downgrade removes this increment's data; never run automatically.
    for table in ("observations", "jobs", "trips", "users"):
        op.drop_table(table,schema="vial")
