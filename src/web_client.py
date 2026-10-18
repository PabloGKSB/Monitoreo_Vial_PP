"""Serve a same-origin client and an explicit allowlist of public configuration."""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_client(application, verifier, publishable_key, max_upload):
    if publishable_key and not publishable_key.startswith("sb_publishable_"):
        raise ValueError("El cliente requiere una clave sb_publishable_; no usar claves secretas o service_role")
    directory = Path(__file__).resolve().parent.parent / "web" / "dist"
    application.mount("/assets", StaticFiles(directory=directory / "assets", check_dir=False), name="client-assets")

    @application.get("/", include_in_schema=False)
    def index():
        if not (directory / "index.html").is_file():
            raise HTTPException(503, "Interfaz web no disponible")
        return FileResponse(directory / "index.html", media_type="text/html")

    @application.get("/v1/client-config", include_in_schema=False)
    def client_config():
        if not publishable_key:
            raise HTTPException(503, "Acceso web no configurado")
        return {"supabase_url": verifier.issuer.removesuffix("/auth/v1"),
                "publishable_key": publishable_key, "max_upload_bytes": max_upload}

    return ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            f"connect-src 'self' {verifier.issuer.removesuffix('/auth/v1')}; "
            "img-src 'self' data: https://tile.openstreetmap.org; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
