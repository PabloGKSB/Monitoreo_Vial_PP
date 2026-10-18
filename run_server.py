"""Production entrypoint; migrations remain an explicit administrative action."""

import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

from src.database import database_engine
from src.deployment import deployment_preflight


def drop_volume_bootstrap_privileges():
    # Railway mounts volumes as root. Its RAILWAY_RUN_UID=0 is used only for
    # these two directories; the API always drops to the image's uid/gid.
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        mount = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH') or os.environ.get('VIAL_VOLUME_ROOT')
        root = Path(os.environ.get('VIAL_API_STORAGE', ''))
        if mount != '/data' or root != Path('/data/archives'):
            raise ValueError('El arranque root solo prepara /data/archives')
        for directory in (Path('/data'), root):
            if directory.is_symlink():
                raise ValueError('El volumen no debe ser un enlace simbolico')
            directory.mkdir(exist_ok=True)
            os.chown(directory, 10001, 10001)
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)


def main():
    # Container variables take precedence. Never read a developer's .env implicitly.
    if os.environ.get("VIAL_ENV_FILE"):
        load_dotenv(os.environ["VIAL_ENV_FILE"], override=False)
    drop_volume_bootstrap_privileges()
    engine = database_engine(os.environ["VIAL_DATABASE_URL"])
    try:
        deployment_preflight(os.environ, engine)
    finally:
        engine.dispose()
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT fuera de rango")
    uvicorn.run("src.central_api:app_from_env", factory=True, host="0.0.0.0", port=port,
                workers=1, proxy_headers=True,
                forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"),
                access_log=False, timeout_keep_alive=5)


if __name__ == "__main__":
    main()
