"""Read-only readiness check through the actual backend connection; no secrets logged."""

import json
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.engine import make_url

from src.database import database_engine


def main():
    engine = None
    try:
        values = dotenv_values(Path(__file__).resolve().parent.parent / '.env', interpolate=False)
        url = make_url(values['VIAL_DATABASE_URL'])
        verified_ca = url.query.get('sslmode') == 'verify-full' and Path(url.query.get('sslrootcert', '')).is_file()
        if not verified_ca:
            raise ValueError('Verified CA required')
        engine = database_engine(values['VIAL_DATABASE_URL'])
        with engine.connect() as connection:
            connection.exec_driver_sql('SET TRANSACTION READ ONLY')
            role = connection.execute(text(
                'SELECT current_user, rolbypassrls, rolsuper, rolcreaterole, rolcreatedb '
                'FROM pg_roles WHERE rolname=current_user')).one()
            client_tls = bool(connection.connection.driver_connection.pgconn.ssl_in_use)
            upstream_tls = connection.scalar(text('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))
            connection.execute(text('SELECT id, owner_id FROM vial.jobs LIMIT 0'))
            connection.execute(text('SELECT geom FROM vial.observations LIMIT 0'))
            result = {'backend_role': role[0],
                      'role_unprivileged': tuple(role) == ('vial_backend', False, False, False, False),
                      'sslmode_verify_full': True, 'client_tls': client_tls,
                      'pooler_to_postgres_tls': upstream_tls,
                      'schema_accessible': True, 'read_only': True}
            connection.rollback()
        result['ready'] = (result['role_unprivileged'] and client_tls and upstream_tls is True)
        print(json.dumps(result))
        return 0 if result['ready'] else 1
    except Exception as error:
        # Database errors and URL parsers may embed secrets in their messages.
        print(json.dumps({'ready': False, 'error_type': type(error).__name__,
                          'details_withheld': True, 'read_only': True}))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
