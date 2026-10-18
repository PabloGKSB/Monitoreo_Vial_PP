"""Explicit adapter for immutable Anotador Vial capture-preview-2 archives."""

import io
from pathlib import PurePosixPath

import numpy as np
import pandas as pd

from .loader import TripData, TripLoadError


def load_native_trip(archive, path, manifest, metadata, require_minimum):
    if not isinstance(metadata, dict) or metadata.get("schema_version") != "capture-preview-2":
        raise TripLoadError("Unsupported native schema_version; expected capture-preview-2")
    try:
        origin = int(metadata["origin_monotonic_ns"])
        epoch = int(metadata["origin_epoch_ms"])
        annotation_origin = int(metadata["annotation_origin_monotonic_ms"])
        annotation_name = metadata["annotations_file"]
        if not isinstance(annotation_name, str) or PurePosixPath(annotation_name).name != annotation_name:
            raise ValueError("Invalid annotation filename")
        root = PurePosixPath(manifest).parent
        mapping = {
            "accelerometer.csv": "total_acceleration",
            "linear_acceleration.csv": "accelerometer",
            "gyroscope.csv": "gyroscope", "gravity.csv": "gravity",
            "rotation_vector.csv": "orientation", "gps.csv": "gps",
            annotation_name: "annotation",
        }
        sensors, sources = {}, {}
        warnings = [str(w) for w in metadata.get("quality_warnings", [])]
        for filename, sensor in mapping.items():
            name = str(root / filename)
            if name not in archive.namelist():
                continue
            if archive.namelist().count(name) != 1:
                raise ValueError(f"Duplicate file: {name}")
            frame = pd.read_csv(io.BytesIO(archive.read(name)))
            if sensor == "annotation":
                required = {"trip_id", "epoch_ms", "elapsed_ms", "event_type"}
                if not required <= set(frame):
                    raise ValueError("Missing annotation columns")
                if frame.trip_id.nunique() > 1:
                    raise ValueError("Mixed annotation trip IDs")
                frame["timestamp_text_raw"] = frame.get("timestamp")
                frame["timestamp"] = pd.to_datetime(frame.epoch_ms, unit="ms", utc=True)
                frame["seconds_elapsed"] = (
                    pd.to_numeric(frame.elapsed_ms, errors="raise") / 1000
                    + (annotation_origin * 1_000_000 - origin) / 1e9
                )
            else:
                required = {"sensor_timestamp_ns", "epoch_ms_derived", "seconds_elapsed"}
                required |= ({"latitude", "longitude"} if sensor == "gps" else
                             {"qx", "qy", "qz", "qw"} if sensor == "orientation" else {"x", "y", "z"})
                if not required <= set(frame):
                    raise ValueError(f"Missing columns in {filename}: {required - set(frame)}")
                for col in required:
                    frame[col] = pd.to_numeric(frame[col], errors="raise")
                if not np.isfinite(frame[list(required)].to_numpy(dtype=float)).all():
                    raise ValueError(f"Non-finite required values in {filename}")
                if not pd.api.types.is_integer_dtype(frame.sensor_timestamp_ns.dtype):
                    raise ValueError("Native nanosecond timestamps must be integers")
                delta = frame.sensor_timestamp_ns - origin
                expected = delta / 1e9
                if not np.allclose(frame.seconds_elapsed, expected, atol=1e-9, rtol=0):
                    raise ValueError(f"Elapsed clock mismatch in {filename}")
                if not (frame.epoch_ms_derived == epoch + np.trunc(delta / 1e6).astype('int64')).all():
                    raise ValueError(f"Epoch clock mismatch in {filename}")
                if (frame.sensor_timestamp_ns.diff().dropna() <= 0).any():
                    raise ValueError(f"Non-increasing timestamps in {filename}; RAW retained")
                frame["timestamp"] = pd.to_datetime(epoch, unit="ms", utc=True) + pd.to_timedelta(delta, unit="ns")
                if sensor == "gps":
                    for source, target in {"speed_mps": "speed", "horizontal_accuracy_m": "horizontal_accuracy"}.items():
                        if source in frame:
                            frame[target] = pd.to_numeric(frame[source], errors="raise")
                frame.attrs["acceleration_semantics"] = "linear" if sensor == "accelerometer" else "total"
            sensors[sensor], sources[sensor] = frame, name
        if "accelerometer" not in sensors and "total_acceleration" in sensors:
            sensors["accelerometer"] = sensors["total_acceleration"].copy()
            sources["accelerometer"] = sources["total_acceleration"]
            warnings.append("Linear acceleration unavailable; total acceleration retained")
        if metadata.get("queue_dropped", 0):
            warnings.append(f"Muestras descartadas por cola llena: {metadata['queue_dropped']}")
        if metadata.get("state") != "COMPLETED" or metadata.get("error") or metadata.get("pending_unwritten", 0):
            warnings.append("Captura incompleta o con error de escritura; revisar metadata")
        warnings.append("Formato nativo: inspeccion de trayecto y calidad; deteccion automatica pendiente de validacion")
        annotations = sensors.get("annotation")
        trip_id = str(annotations.trip_id.iloc[0]) if annotations is not None and not annotations.empty else path.stem
        trip = TripData(trip_id, path, sensors, sources, warnings, metadata)
        if require_minimum:
            trip.require_minimum_sensors()
        return trip
    except (KeyError, TypeError, ValueError, OverflowError, pd.errors.ParserError) as exc:
        raise TripLoadError(f"Invalid native capture: {exc}") from exc
