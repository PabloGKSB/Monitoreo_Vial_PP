"""Folium rendering kept separate from processing and detection."""

from __future__ import annotations

from pathlib import Path

import folium
import pandas as pd

from .analyzer import AnalysisResult

CONDITION_COLORS = {"BUENO": "#25855a", "REGULAR": "#d28b13", "MALO": "#c43d4b"}
SEVERITY_COLORS = {"LEVE": "#f0ad2c", "MEDIA": "#e3692d", "ALTA": "#b6243a"}


def build_trip_map(result: AnalysisResult) -> folium.Map:
    """Render route, experimental segments and geolocated anomaly events."""

    gps = result.gps.dropna(subset=["latitude", "longitude"])
    if gps.empty:
        return folium.Map(location=[-33.45, -70.66], zoom_start=5, tiles="CartoDB positron")
    center = [float(gps["latitude"].median()), float(gps["longitude"].median())]
    trip_map = folium.Map(location=center, zoom_start=14, tiles="CartoDB positron", control_scale=True)
    route_layer = folium.FeatureGroup(name="Trayectoria GPS", show=True)
    folium.PolyLine(
        gps[["latitude", "longitude"]].values.tolist(), color="#315d86", weight=3, opacity=0.65
    ).add_to(route_layer)
    route_layer.add_to(trip_map)

    segment_layer = folium.FeatureGroup(name="Estado experimental", show=True)
    for row in result.segments.itertuples():
        color = CONDITION_COLORS.get(row.condition, "#777777")
        folium.PolyLine(
            [(row.start_latitude, row.start_longitude), (row.end_latitude, row.end_longitude)],
            color=color, weight=7, opacity=0.85,
            tooltip=(f"{row.segment_id} | {row.condition} | score {row.road_condition_score:.1f} | "
                     f"eventos {row.event_count}"),
        ).add_to(segment_layer)
    segment_layer.add_to(trip_map)

    event_layer = folium.FeatureGroup(name="Posibles irregularidades", show=True)
    located = result.events[result.events["gps_status"] == "OK"]
    for row in located.itertuples():
        folium.CircleMarker(
            location=(row.latitude, row.longitude), radius=5 + min(row.event_score, 8) / 2,
            color="#ffffff", weight=1, fill=True,
            fill_color=SEVERITY_COLORS.get(row.severity, "#555555"), fill_opacity=0.95,
            tooltip=(f"{row.event_id} | {row.severity} | score {row.event_score:.2f} | "
                     f"{row.speed_kmh:.1f} km/h"),
        ).add_to(event_layer)
    event_layer.add_to(trip_map)
    folium.LayerControl(collapsed=False).add_to(trip_map)
    trip_map.fit_bounds(gps[["latitude", "longitude"]].values.tolist())
    return trip_map


def save_trip_map(result: AnalysisResult, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    build_trip_map(result).save(str(destination))
    return destination

