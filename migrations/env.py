"""Migration connection comes only from the server environment."""

import os
from alembic import context
from src.database import database_engine, metadata


def run():
    url = os.environ.get("VIAL_MIGRATION_DATABASE_URL") or os.environ.get("VIAL_DATABASE_URL")
    if not url:
        raise RuntimeError("Configurar VIAL_MIGRATION_DATABASE_URL antes de ejecutar migraciones")
    if context.is_offline_mode():
        raise RuntimeError("Migracion PostGIS requiere conexion para descubrir el esquema de extension")
    engine = database_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata, version_table_schema="public")
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run()
