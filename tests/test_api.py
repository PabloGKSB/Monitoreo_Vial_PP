import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import time
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient
import pandas as pd
import pytest

from src import api


def capture_bytes(*, version="capture-preview-2", invalid_gps=False, legacy=False):
    stream = io.BytesIO()
    epoch, origin = 1790614908223, 242845907000000
    elapsed = [0, 1, 75, 76]
    clock = {"sensor_timestamp_ns": [origin + t * 10**9 for t in elapsed],
             "epoch_ms_derived": [epoch + t * 1000 for t in elapsed], "seconds_elapsed": elapsed}
    with ZipFile(stream, "w") as archive:
        if not legacy:
            archive.writestr("metadata.json", json.dumps({
                "schema_version": version, "origin_monotonic_ns": str(origin),
                "origin_epoch_ms": epoch, "annotation_origin_monotonic_ms": origin // 10**6,
                "annotations_file": "marks.csv", "state": "COMPLETED", "queue_dropped": 2,
            }))
        accel = pd.DataFrame({**clock, "x": [0]*4, "y": [0]*4, "z": [0.1]*4})
        gps = pd.DataFrame({**clock, "latitude": [100]*4 if invalid_gps else [-38.7, -38.7001, -38.71, -38.7101],
                            "longitude": [-72.6]*4, "speed_mps": [None]*4,
                            "horizontal_accuracy_m": [4]*4})
        archive.writestr("accelerometer.csv" if legacy else "linear_acceleration.csv", accel.to_csv(index=False))
        archive.writestr("Location.csv" if legacy else "gps.csv", gps.to_csv(index=False))
        if not legacy:
            marks = pd.DataFrame({"trip_id": ["fixture"], "epoch_ms": [epoch + 1000],
                                  "elapsed_ms": [1000], "event_type": ["BACHE"]})
            archive.writestr("marks.csv", marks.to_csv(index=False))
    return stream.getvalue()


def await_job(client, job_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        record = client.get(f"/v1/jobs/{job_id}").json()
        if record["status"] in {"COMPLETED", "FAILED"}:
            return record
        time.sleep(0.01)
    pytest.fail("Local job did not finish")


def submit(client, payload=None, filename="native.zip"):
    return client.post("/v1/jobs", files={"file": (filename, payload or capture_bytes(), "application/zip")})


def test_native_upload_result_map_and_persistence(tmp_path):
    data = capture_bytes()
    with TestClient(api.create_app(tmp_path)) as client:
        response = submit(client, data)
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        assert response.headers["Location"] == f"/v1/jobs/{job_id}"
        assert await_job(client, job_id)["status"] == "COMPLETED"
        result = client.get(f"/v1/jobs/{job_id}/result").json()
        assert result["capture_profile"] == "capture-preview-2"
        assert result["detection"] == {"status": "NOT_EVALUATED", "event_count": None}
        assert result["summary"]["route_part_count"] == 2
        assert result["summary"]["queue_dropped"] == 2
        assert result["summary"]["mean_fix_speed_kmh"] is None
        assert len(result["trajectory"]["features"]) == 2
        assert 0.02 < result["summary"]["observed_distance_km"] < 0.025
        assert result["annotations"][0]["event_type"] == "BACHE"
        assert result["gps_fixes"][0]["timestamp"].startswith("2026-09-28")
        html = client.get(f"/v1/jobs/{job_id}/map").text
        assert html.count("L.polyline(") == 2
        assert "Inicio GPS" in html and "Fin GPS" in html
        assert (tmp_path / job_id / "input.zip").read_bytes() == data
    with TestClient(api.create_app(tmp_path)) as client:
        assert client.get(f"/v1/jobs/{job_id}/result").status_code == 200


def test_legacy_stays_inspection_and_preserves_display_id(tmp_path):
    with TestClient(api.create_app(tmp_path)) as client:
        job_id = submit(client, capture_bytes(legacy=True), "route.zip").json()["job_id"]
        assert await_job(client, job_id)["status"] == "COMPLETED"
        result = client.get(f"/v1/jobs/{job_id}/result").json()
        assert result["trip_id"] == "route"
        assert result["capture_profile"] == "sensor-logger-legacy"
        assert result["analysis_mode"] == "inspection"
        assert result["detection"]["event_count"] is None


@pytest.mark.parametrize("filename,data,code", [
    ("native.rar", b"bytes", 415), ("bad.zip", b"not a zip", 422), ("empty.zip", b"", 422),
])
def test_bad_upload_cleanup(tmp_path, filename, data, code):
    with TestClient(api.create_app(tmp_path)) as client:
        response = client.post("/v1/jobs", files={"file": (filename, data, "application/zip")})
        assert response.status_code == code
        assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", ["../escape.csv", "C:/escape.csv", "/escape.csv"])
def test_zip_paths_rejected_without_extracting(tmp_path, name):
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(name, "x")
    with TestClient(api.create_app(tmp_path)) as client:
        assert submit(client, stream.getvalue()).status_code == 422
        assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("limits", [{"max_upload": 10}, {"max_unpacked": 10}, {"max_entries": 1}])
def test_container_limits(tmp_path, limits):
    with TestClient(api.create_app(tmp_path, **limits)) as client:
        response = submit(client)
        assert response.status_code == (422 if "max_entries" in limits else 413)
        assert not list(tmp_path.iterdir())


def test_semantic_rejection_is_failed_job(tmp_path):
    with TestClient(api.create_app(tmp_path)) as client:
        job_id = submit(client, capture_bytes(version="future-3")).json()["job_id"]
        record = await_job(client, job_id)
        assert record["status"] == "FAILED"
        assert record["error"]["code"] == "INVALID_TRIP"
        assert client.get(f"/v1/jobs/{job_id}/result").status_code == 409


def test_invalid_quality_is_inspectable_without_automatic_events(tmp_path):
    with TestClient(api.create_app(tmp_path)) as client:
        job_id = submit(client, capture_bytes(invalid_gps=True)).json()["job_id"]
        assert await_job(client, job_id)["status"] == "COMPLETED"
        result = client.get(f"/v1/jobs/{job_id}/result").json()
        assert result["quality"]["overall_status"] == "INVALID"
        assert result["trajectory"]["features"] == []
        assert result["detection"]["event_count"] is None


def test_pending_capacity_and_status_response(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = api.inspect_archive

    def blocked(path, filename=None):
        entered.set()
        assert release.wait(10)
        return original(path, filename)

    monkeypatch.setattr(api, "inspect_archive", blocked)
    with TestClient(api.create_app(tmp_path, max_pending=1)) as client:
        try:
            job_id = submit(client).json()["job_id"]
            assert entered.wait(5)
            assert client.get("/health").status_code == 200
            assert client.get(f"/v1/jobs/{job_id}/result").status_code == 409
            busy = submit(client)
            assert busy.status_code == 429 and busy.headers["Retry-After"] == "5"
        finally:
            release.set()
        assert await_job(client, job_id)["status"] == "COMPLETED"


def test_interrupted_job_on_restart(tmp_path):
    with TestClient(api.create_app(tmp_path)) as client:
        job_id = submit(client).json()["job_id"]
        record = await_job(client, job_id)
    record["status"] = "PROCESSING"
    (tmp_path / job_id / "job.json").write_text(json.dumps(record), encoding="utf-8")
    with TestClient(api.create_app(tmp_path)) as client:
        recovered = client.get(f"/v1/jobs/{job_id}").json()
        assert recovered["status"] == "FAILED"
        assert recovered["error"]["code"] == "PROCESS_INTERRUPTED"
        assert client.get(f"/v1/jobs/{job_id}/result").status_code == 409


def test_status_reads_during_atomic_updates(tmp_path):
    jobs = api.LocalJobs(tmp_path, max_pending=1)
    job_id = uuid4()
    directory = tmp_path / str(job_id)
    directory.mkdir()
    jobs.write(directory / "job.json", {"revision": 0})
    start = threading.Barrier(4)

    def update():
        start.wait(timeout=5)
        for revision in range(1, 101):
            jobs.write(directory / "job.json", {"revision": revision})

    def read():
        start.wait(timeout=5)
        for _ in range(200):
            assert 0 <= jobs.read(job_id)["revision"] <= 100

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(update)] + [executor.submit(read) for _ in range(3)]
            for future in futures:
                future.result(timeout=15)
        assert jobs.read(job_id)["revision"] == 100
    finally:
        jobs.worker.shutdown(wait=True)


def test_failure_message_and_unknown_job(tmp_path, monkeypatch):
    def broken(*args):
        raise RuntimeError("sensitive internal details")

    monkeypatch.setattr(api, "inspect_archive", broken)
    with TestClient(api.create_app(tmp_path)) as client:
        job_id = submit(client).json()["job_id"]
        record = await_job(client, job_id)
        assert record["error"]["code"] == "INSPECTION_FAILED"
        assert "sensitive" not in str(record)
        assert client.get(f"/v1/jobs/{uuid4()}").status_code == 404
        assert client.get("/v1/jobs/not-a-uuid").status_code == 422
