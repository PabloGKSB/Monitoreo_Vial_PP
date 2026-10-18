"""Local, single-process API for ZIP inspection using the existing V0 readers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import logging
import math
import os
from pathlib import Path, PurePosixPath
from threading import BoundedSemaphore, RLock
from typing import Literal
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile

import folium
from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse
import pandas as pd
from pydantic import BaseModel, Field

from .gps import prepare_gps, route_summary
from .loader import TripLoadError, load_trip
from .quality import assess_trip
from .processing_policy import processing_policy

LOGGER = logging.getLogger(__name__)
JobStatus = Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]


class JobView(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: str
    updated_at: str
    filename: str
    upload_bytes: int
    sha256: str
    error: dict[str, str] | None = None


class InspectionResult(BaseModel):
    contract_version: Literal["inspection-api-1"] = "inspection-api-1"
    analysis_mode: Literal["inspection"] = "inspection"
    capture_profile: str
    trip_id: str
    summary: dict
    quality: dict
    warnings: list[str]
    sensors: dict[str, dict]
    trajectory: dict
    gps_fixes: list[dict]
    annotations: list[dict]
    detection: dict = {"status": "NOT_EVALUATED", "event_count": None}
    processing_policy: dict = Field(default_factory=lambda: {
        "version": "unknown", "detection_allowed": False, "reasons": ["LEGACY_INSPECTION_RESULT"]})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def inspect_archive(path: Path, filename: str | None = None) -> InspectionResult:
    trip = load_trip(path)
    if not trip.metadata and filename:
        trip.trip_id = Path(filename).stem
    quality = assess_trip(trip)
    gps = prepare_gps(trip.sensors["gps"])
    features = []
    for part, rows in gps.groupby("route_part", sort=True):
        coordinates = rows[["longitude", "latitude"]].to_numpy().tolist()
        features.append({
            "type": "Feature", "properties": {"route_part": int(part), "fix_count": len(rows)},
            "geometry": {"type": "LineString" if len(rows) > 1 else "Point",
                         "coordinates": coordinates if len(rows) > 1 else coordinates[0]},
        })
    fix_columns = ["timestamp", "seconds_elapsed", "latitude", "longitude", "route_part",
                   "horizontal_accuracy", "speed_kmh", "route_distance_m"]
    fixes = json.loads(gps.reindex(columns=fix_columns).to_json(orient="records", date_format="iso"))
    annotations = trip.sensors.get("annotation", pd.DataFrame())
    annotation_columns = ["trip_id", "timestamp", "seconds_elapsed", "event_type"]
    marks = json.loads(annotations.reindex(columns=annotation_columns).to_json(
        orient="records", date_format="iso"))
    route = route_summary(gps)
    return InspectionResult(
        capture_profile=trip.metadata.get("schema_version", "sensor-logger-legacy"),
        trip_id=trip.trip_id,
        summary={"duration_seconds": quality.duration_seconds,
                 "observed_distance_km": route["distance_km"],
                 "mean_fix_speed_kmh": _finite(route["mean_speed_kmh"]),
                 "gps_fix_count": len(gps), "route_part_count": len(features),
                 "quality_status": quality.overall_status.value,
                 "queue_dropped": trip.metadata.get("queue_dropped"),
                 "capture_state": trip.metadata.get("state")},
        quality=quality.to_dict(), warnings=trip.warnings,
        sensors={name: {"record_count": len(frame), "source_file": trip.source_files.get(name)}
                 for name, frame in trip.sensors.items()},
        trajectory={"type": "FeatureCollection", "features": features},
        gps_fixes=fixes, annotations=marks,
        processing_policy=processing_policy(trip, quality, inspection_only=True),
    )


class LocalJobs:
    """Atomic local JSON records; one process owns this directory and its worker."""

    def __init__(self, root: Path, max_pending: int):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        # Windows cannot replace a JSON file while a status reader holds it open.
        self.record_lock = RLock()
        self.slots = BoundedSemaphore(max_pending)
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="zip-inspection")
        # Interrupted jobs remain inspectable; retries require a new explicit upload.
        for path in self.root.glob("*/job.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["status"] in {"QUEUED", "PROCESSING"}:
                record.update(status="FAILED", updated_at=_now(), error={
                    "code": "PROCESS_INTERRUPTED", "message": "El proceso local se interrumpio; volver a cargar el ZIP."})
                self.write(path, record)

    def write(self, path: Path, payload: dict) -> None:
        with self.record_lock:
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            temporary.replace(path)

    def read(self, job_id: UUID) -> dict:
        path = self.root / str(job_id) / "job.json"
        with self.record_lock:
            if not path.exists():
                raise HTTPException(404, "Trabajo no encontrado")
            return json.loads(path.read_text(encoding="utf-8"))

    def process(self, job_id: UUID) -> None:
        directory = self.root / str(job_id)
        record = self.read(job_id)
        try:
            record.update(status="PROCESSING", updated_at=_now())
            self.write(directory / "job.json", record)
            result = inspect_archive(directory / "input.zip", record["filename"])
            self.write(directory / "result.json", result.model_dump(mode="json"))
            record.update(status="COMPLETED", updated_at=_now())
        except TripLoadError as exc:
            record.update(status="FAILED", updated_at=_now(), error={
                "code": "INVALID_TRIP", "message": str(exc)})
        except Exception:
            LOGGER.exception("Inspection failed for job %s", job_id)
            record.update(status="FAILED", updated_at=_now(), error={
                "code": "INSPECTION_FAILED", "message": "No se pudo inspeccionar el recorrido; revisar el registro local."})
        finally:
            try:
                self.write(directory / "job.json", record)
            finally:
                self.slots.release()


def validate_container(path: Path, max_unpacked: int, max_entries: int) -> None:
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > max_entries:
                raise HTTPException(422, "Cantidad de entradas ZIP no admitida")
            if sum(entry.file_size for entry in entries) > max_unpacked:
                raise HTTPException(413, "ZIP descomprimido excede el limite")
            seen = set()
            for entry in entries:
                name = entry.filename.replace("\\", "/")
                parts = PurePosixPath(name)
                if parts.is_absolute() or ".." in parts.parts or ":" in name or name in seen:
                    raise HTTPException(422, "Rutas inseguras o duplicadas en ZIP")
                if entry.flag_bits & 1 or entry.external_attr >> 16 & 0o170000 == 0o120000:
                    raise HTTPException(422, "ZIP cifrado o enlace simbolico no admitido")
                if entry.file_size > max(1, entry.compress_size) * 1000:
                    raise HTTPException(413, "Compresion ZIP excesiva")
                if parts.name == "metadata.json" and entry.file_size > 1024 * 1024:
                    raise HTTPException(413, "metadata.json excede el limite")
                seen.add(name)
    except BadZipFile as exc:
        raise HTTPException(422, "Archivo ZIP invalido") from exc


def render_map(data: dict) -> str:
    fixes = data["gps_fixes"]
    center = [fixes[0]["latitude"], fixes[0]["longitude"]] if fixes else [0, 0]
    view = folium.Map(location=center, zoom_start=14 if fixes else 2, tiles="OpenStreetMap")
    for feature in data["trajectory"]["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "LineString":
            folium.PolyLine([[lat, lon] for lon, lat in geometry["coordinates"]],
                            color="#1976d2", weight=4).add_to(view)
        else:
            lon, lat = geometry["coordinates"]
            folium.CircleMarker([lat, lon], radius=4, color="#1976d2").add_to(view)
    if fixes:
        for fix, label in [(fixes[0], "Inicio GPS"), (fixes[-1], "Fin GPS")]:
            folium.Marker([fix["latitude"], fix["longitude"]],
                          popup=f"{label}: {escape(data['trip_id'])}").add_to(view)
        view.fit_bounds([[fix["latitude"], fix["longitude"]] for fix in fixes])
    return view.get_root().render()


def create_app(storage_dir: Path | None = None, *, max_upload: int = 64 * 1024 * 1024,
               max_unpacked: int = 256 * 1024 * 1024, max_entries: int = 1000,
               max_pending: int = 4) -> FastAPI:
    root = storage_dir or Path(os.environ.get("VIAL_API_STORAGE", ".api_local"))

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.jobs = LocalJobs(root.resolve(), max_pending)
        try:
            yield
        finally:
            application.state.jobs.worker.shutdown(wait=True)

    application = FastAPI(
        title="Monitoreo Vial - API local de inspeccion", version="0.1.0",
        description="Prueba local de Etapa 3. Sin cuentas de usuario; ejecutar solo en 127.0.0.1 y con un proceso.",
        lifespan=lifespan,
    )

    @application.get("/health")
    def health():
        return {"status": "ok", "mode": "local_inspection", "contract_version": "inspection-api-1",
                "max_upload_bytes": max_upload, "max_unpacked_bytes": max_unpacked,
                "max_entries": max_entries, "max_pending_jobs": max_pending}

    @application.post("/v1/jobs", response_model=JobView, status_code=202)
    async def upload(file: UploadFile, response: Response):
        jobs = application.state.jobs
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1][:200]
        if not filename.lower().endswith(".zip"):
            await file.close()
            raise HTTPException(415, "Se requiere un archivo .zip")
        if not jobs.slots.acquire(blocking=False):
            await file.close()
            raise HTTPException(429, "Capacidad de trabajos pendientes alcanzada; esperar y reintentar",
                                headers={"Retry-After": "5"})
        job_id = uuid4()
        directory = jobs.root / str(job_id)
        submitted = False
        try:
            directory.mkdir()
            size, digest = 0, sha256()
            with (directory / "input.zip").open("xb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_upload:
                        raise HTTPException(413, "ZIP supera el limite de carga")
                    digest.update(chunk)
                    output.write(chunk)
            validate_container(directory / "input.zip", max_unpacked, max_entries)
            record = {"job_id": str(job_id), "status": "QUEUED", "created_at": _now(),
                      "updated_at": _now(), "filename": filename, "upload_bytes": size,
                      "sha256": digest.hexdigest(), "error": None}
            jobs.write(directory / "job.json", record)
            jobs.worker.submit(jobs.process, job_id)
            submitted = True
            response.headers["Location"] = f"/v1/jobs/{job_id}"
            return record
        finally:
            await file.close()
            if not submitted:
                try:
                    if directory.exists():
                        for path in directory.iterdir():
                            path.unlink()
                        directory.rmdir()
                finally:
                    jobs.slots.release()

    @application.get("/v1/jobs/{job_id}", response_model=JobView)
    def job(job_id: UUID):
        return application.state.jobs.read(job_id)

    @application.get("/v1/jobs/{job_id}/result", response_model=InspectionResult)
    def result(job_id: UUID):
        record = application.state.jobs.read(job_id)
        if record["status"] != "COMPLETED":
            raise HTTPException(409, {"status": record["status"], "error": record["error"]})
        path = application.state.jobs.root / str(job_id) / "result.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @application.get("/v1/jobs/{job_id}/map", response_class=HTMLResponse)
    def trip_map(job_id: UUID):
        return render_map(result(job_id))

    return application


app = create_app()
