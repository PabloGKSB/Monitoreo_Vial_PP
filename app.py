"""Streamlit presentation layer for the road-monitoring V0 prototype."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.analyzer import AnalysisResult, TripAnalyzer
from src.config import AnalysisConfig
from src.loader import TripLoadError, discover_trip_archives
from src.maps import build_trip_map, save_trip_map

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
LEGACY_DATA_DIR = ROOT / "Data"
UPLOAD_DIR = ROOT / "data" / "processed" / "uploads"


@st.cache_resource(show_spinner="Analizando recorrido...")
def _analyze(path_text: str, modified_ns: int, config: AnalysisConfig) -> AnalysisResult:
    del modified_ns
    return TripAnalyzer(config).analyze(path_text)


def _uploaded_path(uploaded_file) -> Path:
    payload = uploaded_file.getvalue()
    digest = hashlib.sha256(payload).hexdigest()[:12]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{Path(uploaded_file.name).stem}_{digest}.zip"
    if not path.exists():
        path.write_bytes(payload)
    return path


def _duration_text(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes} min {secs:02d} s"


def _quality_table(result: AnalysisResult) -> pd.DataFrame:
    rows = []
    for name, item in result.quality.sensors.items():
        rows.append({
            "Sensor": name.replace("_", " ").title(), "Estado": item.status.value,
            "Registros": item.record_count,
            "Frecuencia (Hz)": round(item.sampling_hz, 2) if item.sampling_hz else None,
            "Cortes": len(item.gaps), "Observaciones": "; ".join(item.issues) or "Sin incidencias",
        })
    return pd.DataFrame(rows)


def _signal_figure(result: AnalysisResult, event_time: float) -> go.Figure:
    frame = result.processed_accelerometer
    view = frame[frame["seconds_elapsed"].between(event_time - 5, event_time + 5)]
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=view["seconds_elapsed"], y=view["dynamic_magnitude"], name="Magnitud dinamica", line={"color": "#315d86", "width": 1.5}))
    figure.add_trace(go.Scatter(x=view["seconds_elapsed"], y=view["smoothed_magnitude"], name="Suavizada", line={"color": "#d26b32", "width": 2}))
    figure.add_vline(x=event_time, line_width=2, line_dash="dash", line_color="#b6243a")
    figure.update_layout(
        height=380, margin={"l": 20, "r": 20, "t": 30, "b": 20},
        xaxis_title="Segundos transcurridos", yaxis_title="Aceleracion (m/s2)",
        hovermode="x unified", legend={"orientation": "h", "y": 1.12},
    )
    return figure


def _gyro_figure(result: AnalysisResult, event_time: float) -> go.Figure | None:
    if "gyroscope" not in result.trip.sensors:
        return None
    gyro = result.trip.sensors["gyroscope"]
    view = gyro[gyro["seconds_elapsed"].between(event_time - 5, event_time + 5)].copy()
    if view.empty:
        return None
    view["magnitude"] = np.linalg.norm(view[["x", "y", "z"]].to_numpy(float), axis=1)
    figure = go.Figure(go.Scatter(x=view["seconds_elapsed"], y=view["magnitude"], name="Magnitud angular", line={"color": "#6b577b"}))
    figure.add_vline(x=event_time, line_width=2, line_dash="dash", line_color="#b6243a")
    figure.update_layout(height=300, margin={"l": 20, "r": 20, "t": 20, "b": 20}, xaxis_title="Segundos transcurridos", yaxis_title="rad/s")
    return figure


def main() -> None:
    st.set_page_config(page_title="Monitoreo vial V0", page_icon=":material/add_road:", layout="wide")
    st.markdown("""
    <style>
    .stApp { background: #f5f7f8; color: #20262d; }
    [data-testid="stHeader"] { background: rgba(245,247,248,.92); }
    [data-testid="stMetric"] { background: #ffffff; border: 1px solid #dfe4e8; border-radius: 6px; padding: 14px; }
    h1, h2, h3 { letter-spacing: 0 !important; color: #1d2933; }
    .status-note { border-left: 4px solid #d28b13; background: #fffaf0; padding: 10px 14px; }
    </style>
    """, unsafe_allow_html=True)
    st.title("Monitoreo vial")
    st.caption("Prototipo V0 | Deteccion experimental de posibles irregularidades")

    archives = discover_trip_archives(RAW_DIR, LEGACY_DATA_DIR)
    with st.sidebar:
        st.header("Recorrido")
        labels = {path.name: path for path in archives}
        selected_name = st.selectbox("ZIP disponible", ["Seleccionar..."] + list(labels))
        uploaded = st.file_uploader("O subir un ZIP", type=["zip"])
        st.divider()
        st.header("Parametros")
        threshold = st.slider("Umbral de anomalia", 2.0, 8.0, 3.5, 0.1)
        segment_metres = st.number_input("Longitud de segmento (m)", 10, 100, 20, 5)

    selected_path = _uploaded_path(uploaded) if uploaded else labels.get(selected_name)
    if selected_path is None:
        st.info("Selecciona un recorrido disponible o sube un archivo ZIP para comenzar.")
        return
    config = AnalysisConfig(detector_threshold=threshold, road_segment_meters=float(segment_metres))
    try:
        result = _analyze(str(selected_path), selected_path.stat().st_mtime_ns, config)
    except (TripLoadError, ValueError) as exc:
        st.error(f"No fue posible analizar el recorrido: {exc}")
        return

    summary = result.summary
    native_inspection = summary.get("analysis_mode") == "native_inspection"
    detection_evaluated = summary.get("detection_status") == "EVALUATED"
    for warning in result.trip.warnings:
        st.warning(warning)
    st.subheader(result.trip.trip_id.replace("_", " "))
    cols = st.columns(5)
    cols[0].metric("Duracion", _duration_text(float(summary["duration_seconds"])))
    cols[1].metric("Distancia GPS observada", f"{summary['distance_km']:.2f} km")
    cols[2].metric("Velocidad media", f"{summary['mean_speed_kmh']:.1f} km/h")
    cols[3].metric("Detecciones", summary["event_count"] if detection_evaluated else "No evaluadas")
    cols[4].metric("Calidad", summary["quality_status"])
    if summary.get("detection_status") == "BLOCKED_INVALID":
        st.error("Datos requeridos invalidos: deteccion bloqueada. Trayecto y calidad disponibles para revision.")
    elif not detection_evaluated and not native_inspection:
        st.warning("No hay suficientes ventanas continuas con cobertura GPS para evaluar detecciones.")
    st.markdown('<div class="status-note">Indices de severidad y estado vial experimentales; aun no constituyen una escala validada.</div>', unsafe_allow_html=True)

    overview_tab, quality_tab, events_tab, signal_tab = st.tabs(["Mapa", "Calidad", "Eventos", "Senal"])
    with overview_tab:
        st_folium(build_trip_map(result), use_container_width=True, height=620, returned_objects=[])
        st.caption("Trayectoria GPS observada; intervalos mayores de 2 s separados, sin sumar distancia entre sus extremos." if native_inspection else "Azul: trayectoria GPS. Verde/amarillo/rojo: segmentos BUENO/REGULAR/MALO. Puntos: anomalias.")

    with quality_tab:
        st.dataframe(_quality_table(result), width="stretch", hide_index=True)
        for sensor, item in result.quality.sensors.items():
            if item.gaps:
                with st.expander(f"Cortes detectados · {sensor.replace('_', ' ').title()}"):
                    st.dataframe(pd.DataFrame([{
                        "Inicio (s)": gap.start_seconds, "Fin (s)": gap.end_seconds,
                        "Duracion (s)": gap.duration_seconds,
                    } for gap in item.gaps]), width="stretch", hide_index=True)
        st.caption(f"Gravedad: {result.preprocessing_info.gravity_compensation}. Frecuencia usada: {result.preprocessing_info.sampling_hz:.2f} Hz.")

    with events_tab:
        if "annotation" in result.trip.sensors:
            st.subheader("Anotaciones registradas")
            st.dataframe(result.trip.sensors["annotation"], hide_index=True)
        severities = st.multiselect("Severidad", ["LEVE", "MEDIA", "ALTA"], default=["LEVE", "MEDIA", "ALTA"])
        table = result.events[result.events["severity"].isin(severities)].copy()
        display_columns = ["event_id", "timestamp", "severity", "event_score", "speed_kmh", "gps_status"]
        st.dataframe(table.reindex(columns=display_columns), width="stretch", hide_index=True)

    with signal_tab:
        if result.events.empty:
            st.info("Deteccion y procesamiento de senal nativa pendientes de validacion." if native_inspection else ("Deteccion no evaluada; revisar calidad y cobertura." if not detection_evaluated else "No hay eventos para inspeccionar con los parametros actuales."))
        else:
            event_id = st.selectbox("Evento", result.events["event_id"].tolist())
            event = result.events[result.events["event_id"] == event_id].iloc[0]
            st.plotly_chart(_signal_figure(result, float(event["seconds_elapsed"])), width="stretch")
            gyro_figure = _gyro_figure(result, float(event["seconds_elapsed"]))
            if gyro_figure is not None:
                st.plotly_chart(gyro_figure, width="stretch")
            else:
                st.caption("No hay datos de giroscopio disponibles en este intervalo.")

    analyzer = TripAnalyzer(config)
    output_paths = analyzer.export(result, ROOT / "outputs")
    map_path = save_trip_map(result, ROOT / "outputs" / "maps" / f"{result.trip.trip_id}.html")
    with st.sidebar:
        st.success("Analisis listo")
        st.download_button("Descargar eventos CSV", output_paths["events"].read_bytes(), "eventos_detectados.csv", "text/csv")
        st.download_button("Descargar mapa HTML", map_path.read_bytes(), map_path.name, "text/html")


if __name__ == "__main__":
    main()
