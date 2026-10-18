"""Preflight checks for an explicit public, single-process deployment."""

import os
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine import make_url


def public_origin(value):
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("VIAL_PUBLIC_ORIGIN debe ser un origen HTTPS sin rutas ni credenciales")
    return value.rstrip("/")


def deployment_preflight(env, engine):
    public_origin(env.get("VIAL_PUBLIC_ORIGIN", ""))
    if env.get("WEB_CONCURRENCY", "1") != "1":
        raise ValueError("Esta revision admite un solo proceso y una replica")
    if not env.get("SUPABASE_PUBLISHABLE_KEY", "").startswith("sb_publishable_"):
        raise ValueError("Configurar SUPABASE_PUBLISHABLE_KEY para el cliente")
    url = make_url(env["VIAL_DATABASE_URL"])
    if url.query.get("sslmode") != "verify-full" or not Path(url.query.get("sslrootcert", "")).is_file():
        raise ValueError("La conexion requiere sslmode=verify-full y una CA existente")
    root = Path(env.get("VIAL_API_STORAGE", "")).resolve()
    mount = env.get("RAILWAY_VOLUME_MOUNT_PATH") or env.get("VIAL_VOLUME_ROOT")
    if not mount or not Path(mount).is_dir() or not root.is_relative_to(Path(mount).resolve()):
        raise ValueError("Configurar un volumen persistente y VIAL_API_STORAGE dentro de el")
    if env.get("VIAL_PERSISTENT_STORAGE_CONFIRMED") != "1":
        raise ValueError("Confirmar persistencia y respaldo del volumen antes de publicar")
    root.mkdir(parents=True, exist_ok=True)
    if not os.access(root, os.W_OK):
        raise ValueError("El volumen no permite escribir con el usuario de ejecucion")
    with engine.connect() as connection:
        role = connection.execute(text(
            "SELECT current_user, rolbypassrls, rolsuper, rolcreaterole, rolcreatedb "
            "FROM pg_roles WHERE rolname=current_user"
        )).one()
        if tuple(role) != ("vial_backend", False, False, False, False):
            raise ValueError("El servidor debe usar el rol vial_backend sin privilegios administrativos")
        raw = connection.connection.driver_connection
        if not raw.pgconn.ssl_in_use:
            raise ValueError("La conexion del cliente a PostgreSQL/pooler requiere TLS")
        if connection.scalar(text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")) is not True:
            raise ValueError("Activar TLS entre el pooler y PostgreSQL antes de desplegar")
    if not (Path(__file__).resolve().parent.parent / "web/dist/index.html").is_file():
        raise ValueError("Compilar el cliente web antes de desplegar")
