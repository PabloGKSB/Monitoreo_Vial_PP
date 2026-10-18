"""Restrict the backend to the operations used by the central API.

The login password is provisioned separately and never belongs in a revision.
Ownership remains enforced by FastAPI; this role is not a client identity.
"""

from alembic import op

revision = "0002_backend_role"
down_revision = "0001_central"
branch_labels = None
depends_on = None


def upgrade():
    # Fail on an existing role rather than changing an unrelated account.
    op.execute("CREATE ROLE vial_backend NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
    op.execute("""DO $$ BEGIN
        EXECUTE format('GRANT CONNECT ON DATABASE %I TO vial_backend', current_database());
    END $$""")
    op.execute("GRANT USAGE ON SCHEMA vial TO vial_backend")
    op.execute("""DO $$ DECLARE extension_schema text; BEGIN
        SELECT n.nspname INTO STRICT extension_schema
        FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
        WHERE e.extname='postgis';
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO vial_backend', extension_schema);
    END $$""")
    op.execute("REVOKE ALL ON SCHEMA vial FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA vial FROM PUBLIC")
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.alembic_version FROM PUBLIC")
    op.execute("""DO $$ DECLARE client_role text; BEGIN
        FOR client_role IN SELECT rolname FROM pg_roles
            WHERE rolname IN ('anon', 'authenticated', 'service_role') LOOP
            EXECUTE format('REVOKE ALL ON SCHEMA vial FROM %I', client_role);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA vial FROM %I', client_role);
            EXECUTE format('REVOKE ALL ON public.alembic_version FROM %I', client_role);
        END LOOP;
    END $$""")
    op.execute("GRANT SELECT ON vial.users, vial.trips, vial.jobs, vial.observations TO vial_backend")
    op.execute("GRANT INSERT ON vial.users, vial.trips, vial.jobs TO vial_backend")
    op.execute("GRANT UPDATE (trip_id, status, updated_at, error, result) ON vial.jobs TO vial_backend")
    for table in ("users", "trips", "jobs", "observations"):
        op.execute(f"CREATE POLICY backend_select ON vial.{table} FOR SELECT TO vial_backend USING (true)")
    for table in ("users", "trips", "jobs"):
        op.execute(f"CREATE POLICY backend_insert ON vial.{table} FOR INSERT TO vial_backend WITH CHECK (true)")
    op.execute("CREATE POLICY backend_update ON vial.jobs FOR UPDATE TO vial_backend USING (true) WITH CHECK (true)")
    op.execute("ALTER ROLE vial_backend SET search_path = pg_catalog")


def downgrade():
    op.execute("DROP POLICY backend_update ON vial.jobs")
    for table in ("users", "trips", "jobs"):
        op.execute(f"DROP POLICY backend_insert ON vial.{table}")
    for table in ("users", "trips", "jobs", "observations"):
        op.execute(f"DROP POLICY backend_select ON vial.{table}")
    op.execute("REVOKE ALL ON vial.users, vial.trips, vial.jobs, vial.observations FROM vial_backend")
    op.execute("REVOKE UPDATE (trip_id, status, updated_at, error, result) ON vial.jobs FROM vial_backend")
    op.execute("REVOKE ALL ON SCHEMA vial FROM vial_backend")
    op.execute("""DO $$ DECLARE extension_schema text; BEGIN
        SELECT n.nspname INTO STRICT extension_schema
        FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
        WHERE e.extname='postgis';
        EXECUTE format('REVOKE ALL ON SCHEMA %I FROM vial_backend', extension_schema);
        EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM vial_backend', current_database());
    END $$""")
    op.execute("DROP ROLE vial_backend")
