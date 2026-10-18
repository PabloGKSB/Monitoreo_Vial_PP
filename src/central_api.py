"""Authenticated inspection API with central records and a single local worker."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from hashlib import sha256
import logging
import os
import shutil
from pathlib import Path
from threading import BoundedSemaphore
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .api import InspectionResult, JobView, inspect_archive, render_map, validate_container
from .auth import Identity, SupabaseVerifier
from .database import CentralStore, UploadQuotaExceeded, database_engine
from .loader import TripLoadError
from .upload_guard import UploadGuard
from .web_client import mount_client
from .deployment import public_origin

LOGGER = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


def create_central_app(store: CentralStore, verifier: SupabaseVerifier, storage_dir: Path,
                       *, max_pending=4, max_upload=64*1024*1024,
                       max_unpacked=256*1024*1024, max_entries=1000,
                       publishable_key=None, max_jobs_24h=20, max_bytes_24h=256*1024*1024,
                       min_free_storage=256*1024*1024, origin=None) -> FastAPI:
    root = storage_dir.resolve()
    slots = BoundedSemaphore(max_pending)

    def process(job_id: UUID, owner_id: UUID, filename: str):
        try:
            store.mark_processing(job_id, owner_id)
            result = inspect_archive(root / str(job_id) / "input.zip", filename)
            store.complete(job_id, owner_id, result.model_dump(mode="json"))
        except TripLoadError:
            # Do not expose source paths/CSV internals in the central error response.
            store.fail(job_id, owner_id, {"code": "INVALID_TRIP", "message": "Perfil o datos del ZIP no admitidos"})
        except Exception:
            LOGGER.exception("Central inspection failed for job %s", job_id)
            try:
                store.fail(job_id, owner_id, {"code": "INSPECTION_FAILED", "message": "No se pudo inspeccionar el recorrido"})
            except Exception:
                LOGGER.exception("Could not persist failed status for job %s", job_id)
        finally:
            slots.release()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store.check_schema()
        store.interrupt_pending()
        root.mkdir(parents=True, exist_ok=True)
        application.state.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="central-inspection")
        try:
            yield
        finally:
            application.state.worker.shutdown(wait=True)

    application = FastAPI(title="Monitoreo Vial - API central", version="0.2.0", lifespan=lifespan,
                          description="Supabase JWT requerido. Inspeccion, no detector nativo validado. Un proceso/trabajador.")
    application.add_middleware(UploadGuard, max_body_bytes=max_upload + 2*1024*1024, max_parallel=max_pending)
    client_csp = mount_client(application, verifier, publishable_key, max_upload)
    origin = public_origin(origin) if origin else None

    @application.middleware("http")
    async def private_responses(request, call_next):
        if origin and request.url.path != "/health":
            from urllib.parse import urlparse
            if request.url.netloc != urlparse(origin).netloc:
                return JSONResponse({"detail": "Host no admitido"}, status_code=400)
            if request.url.scheme != "https":
                return JSONResponse({"detail": "Se requiere HTTPS"}, status_code=400)
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if origin and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=86400"
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Content-Security-Policy"] = client_csp
        return response

    def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Identity:
        if credentials is None:
            raise HTTPException(401, "Iniciar sesion en Supabase", headers={"WWW-Authenticate": "Bearer"})
        return verifier.verify(credentials.credentials)

    User = Annotated[Identity, Depends(current_user)]

    def owned_job(job_id: UUID, user: Identity):
        record = store.get_job(job_id, user.user_id)
        if record is None:
            raise HTTPException(404, "Trabajo no encontrado")
        return record

    def owned_result(job_id: UUID, user: Identity):
        record = owned_job(job_id, user)
        if record["status"] != "COMPLETED":
            raise HTTPException(409, {"status": record["status"], "error": record["error"]})
        return store.get_result(job_id, user.user_id)

    @application.get("/health")
    def health():
        try:
            store.check_schema()
        except Exception as exc:
            raise HTTPException(503, "Persistencia no disponible") from exc
        return {"status": "ok", "mode": "central_inspection", "authentication": "supabase_jwt",
                "max_upload_bytes": max_upload, "max_pending_jobs": max_pending}

    @application.get("/v1/me")
    def me(user: User):
        return {"user_id": str(user.user_id)}

    @application.get("/v1/jobs", response_model=list[JobView])
    def history(user: User, limit: Annotated[int, Query(ge=1, le=100)] = 20,
                offset: Annotated[int, Query(ge=0)] = 0):
        return store.list_jobs(user.user_id, limit, offset)

    @application.post("/v1/jobs", response_model=JobView, status_code=202)
    async def upload(file: UploadFile, response: Response, user: User):
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1][:200]
        if not filename.lower().endswith(".zip"):
            await file.close()
            raise HTTPException(415, "Se requiere un archivo .zip")
        if shutil.disk_usage(root).free < max_upload*max_pending + min_free_storage:
            await file.close()
            raise HTTPException(507, "Almacenamiento temporalmente insuficiente")
        if not slots.acquire(blocking=False):
            await file.close()
            raise HTTPException(429, "Capacidad de trabajos alcanzada", headers={"Retry-After": "5"})
        job_id = uuid4()
        directory = root / str(job_id)
        submitted, registered = False, False
        try:
            directory.mkdir()
            size, digest = 0, sha256()
            with (directory / "input.zip").open("xb") as output:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > max_upload:
                        raise HTTPException(413, "ZIP supera el limite de carga")
                    output.write(chunk)
                    digest.update(chunk)
            validate_container(directory / "input.zip", max_unpacked, max_entries)
            now = datetime.now(timezone.utc).isoformat()
            record = {"job_id": str(job_id), "status": "QUEUED", "created_at": now, "updated_at": now,
                      "filename": filename, "upload_bytes": size, "sha256": digest.hexdigest(), "error": None}
            try:
                store.create_job(user, record, max_jobs_24h=max_jobs_24h, max_bytes_24h=max_bytes_24h)
            except UploadQuotaExceeded as exc:
                raise HTTPException(429, str(exc), headers={"Retry-After": "3600"}) from exc
            registered = True
            application.state.worker.submit(process, job_id, user.user_id, filename)
            submitted = True
            response.headers["Location"] = f"/v1/jobs/{job_id}"
            return record
        finally:
            await file.close()
            if not submitted:
                try:
                    if registered:
                        store.fail(job_id, user.user_id, {"code": "UPLOAD_INTERRUPTED", "message": "Reintentar carga"})
                    if directory.exists():
                        for path in directory.iterdir():
                            path.unlink()
                        directory.rmdir()
                finally:
                    slots.release()

    @application.get("/v1/jobs/{job_id}", response_model=JobView)
    def status(job_id: UUID, user: User):
        return owned_job(job_id, user)

    @application.get("/v1/jobs/{job_id}/result", response_model=InspectionResult)
    def result(job_id: UUID, user: User):
        return owned_result(job_id, user)

    @application.get("/v1/jobs/{job_id}/map", response_class=HTMLResponse)
    def trip_map(job_id: UUID, user: User):
        return render_map(owned_result(job_id, user))

    @application.get("/v1/jobs/{job_id}/archive")
    def archive(job_id: UUID, user: User):
        record = owned_job(job_id, user)
        path = root / str(job_id) / "input.zip"
        if not path.is_file():
            raise HTTPException(404, "Archivo original no disponible")
        return FileResponse(path, media_type="application/zip", filename=record["filename"])

    return application


def app_from_env() -> FastAPI:
    project_url = os.environ.get("SUPABASE_URL")
    database_url = os.environ.get("VIAL_DATABASE_URL")
    if not project_url or not database_url:
        raise RuntimeError("Modo central requiere SUPABASE_URL y VIAL_DATABASE_URL; no se habilita acceso anonimo")
    engine = database_engine(database_url)
    return create_central_app(CentralStore(engine), SupabaseVerifier(project_url,
                              clock_skew_seconds=int(os.environ.get("VIAL_JWT_LEEWAY_SECONDS", 90))),
                              Path(os.environ.get("VIAL_API_STORAGE", ".api_local/central")),
                              publishable_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY"),
                              origin=os.environ.get("VIAL_PUBLIC_ORIGIN"),
                              max_jobs_24h=_positive_env("VIAL_MAX_JOBS_24H", 20),
                              max_bytes_24h=_positive_env("VIAL_MAX_UPLOAD_MB_24H", 256)*1024*1024,
                              min_free_storage=_positive_env("VIAL_MIN_FREE_STORAGE_MB", 256)*1024*1024)


def _positive_env(name, default):
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} debe ser positivo")
    return value
