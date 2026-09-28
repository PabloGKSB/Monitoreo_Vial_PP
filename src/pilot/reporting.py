"""Pilot reports and local interactive annotation inspection plots."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .data import PilotTrip


def save_annotation_plot(trip: PilotTrip, candidates: pd.DataFrame, output: Path) -> None:
    """Plot measured signals around manual marks; candidate is never called ground truth."""
    baches = candidates[candidates.event_type == "BACHE"]
    if baches.empty:
        return
    figure = make_subplots(rows=3, cols=1, shared_xaxes=True,
                          subplot_titles=("Aceleracion lineal (m/s2)", "Aceleracion total (m/s2)", "Giroscopio (rad/s)"))
    buttons = []
    traces_per_event = 6
    for event_index, event in enumerate(baches.itertuples()):
        for row_index, sensor in enumerate(("accelerometer", "total_acceleration", "gyroscope"), start=1):
            frame = trip.signals[sensor]
            view = frame[frame.seconds_elapsed.between(event.seconds_elapsed - 5, event.seconds_elapsed + 2)]
            xyz = view[["x", "y", "z"]].to_numpy(float)
            channels = {axis: xyz[:, j] for j, axis in enumerate("xyz")} if row_index == 1 else {}
            channels["magnitud"] = np.linalg.norm(xyz, axis=1)
            for name, values in channels.items():
                figure.add_trace(go.Scatter(x=view.seconds_elapsed - event.seconds_elapsed, y=values,
                                           name=f"{sensor}/{name}", visible=event_index == 0,
                                           mode="lines"), row=row_index, col=1)
        title = f"{trip.route_id} | {event.annotation_id} | candidato sin revision"
        buttons.append({"label": event.annotation_id, "method": "update",
                        "args": [{"visible": [i // traces_per_event == event_index
                                               for i in range(len(baches) * traces_per_event)]},
                                 {"title": title}]})
    figure.add_vline(x=0, line_dash="dash", line_color="red")
    figure.update_xaxes(title_text="Segundos respecto del boton BACHE", row=3, col=1)
    figure.update_layout(title=f"{trip.route_id} | anotaciones por revisar", height=850,
                         updatemenus=[{"buttons": buttons, "x": 1, "y": 1.15}], hovermode="x unified")
    figure.write_html(output, include_plotlyjs=True, auto_open=False)


def write_report(output: Path, audits: list[dict], dataset: pd.DataFrame, metrics: pd.DataFrame) -> None:
    lines = ["# Campana piloto 2026-09-25", "", "## Alcance", "",
             "Resultados calculados desde archivos reales. Clasificacion de ventanas asistida por anotaciones;",
             "NO mide deteccion continua ni valida un modelo generalizable. NORMAL es candidato no revisado.",
             "Las cifras exploratorias aportadas por el usuario no se usan como resultados ni umbrales.", "",
             "## Inventario verificado", "",
             "| Recorrido | Minutos sensores | km GPS aprox. | BACHE | Otras marcas |",
             "|---|---:|---:|---:|---:|"]
    for audit in audits:
        counts = audit["annotation_counts"]
        other = sum(v for k, v in counts.items() if k not in {"BACHE", "MONITOREO_INICIO", "MONITOREO_FIN"})
        lines.append(f"| {audit['route_id']} | {audit['duration_seconds']/60:.2f} | {audit['distance_km']:.2f} | {counts.get('BACHE',0)} | {other} |")
    lines += ["", "## Dataset aceptado", "", "| Modo | Recorrido | BACHE | NORMAL candidato |",
              "|---|---|---:|---:|"]
    for (mode, route), part in dataset.groupby(["mode", "route_id"]):
        lines.append(f"| {mode} | {route} | {int(part.label.sum())} | {int((part.label == 0).sum())} |")
    lines += ["", "## Comparacion de ventanas (exploratoria)", "",
              "| Modo | Protocolo | Test | Modelo | Train | TP/FP/FN/TN | Precision | Recall | F1 |",
              "|---|---|---|---|---:|---|---:|---:|---:|"]
    for row in metrics.itertuples():
        if row.status != "OK_EXPLORATORY_WINDOWS":
            lines.append(f"| {row.mode} | {row.protocol} | {row.test_route} | {row.model} | {row.train_n} | Sin clases suficientes | - | - | - |")
        else:
            lines.append(f"| {row.mode} | {row.protocol} | {row.test_route} | {row.model} | {row.train_n} | {int(row.tp)}/{int(row.fp)}/{int(row.fn)}/{int(row.tn)} | {row.precision:.3f} | {row.recall:.3f} | {row.f1:.3f} |")
    lines += ["", "## Interpretacion y limites", "",
              "- fixed_delay resta el retraso fijo configurado al boton. No confirma el instante del impacto.",
              "- peak_assisted busca el maximo en [-3,+1] s por defecto. Es seleccion asistida por etiqueta, no evaluacion operativa.",
              "- LORO_EXPLORATORY separa archivos de recorrido, pero puede repetir sectores o defectos fisicos.",
              "- LORO_SPATIAL_PURGE excluye train cercano a cualquier fijacion GPS de la ruta de test. Ver radio en provenance.json.",
              "- LOCO agrupa ida y vuelta del mismo corredor antes de dividir. Solo hay dos grupos y Prieto comparte sectores con el otro.",
              "- Segun el participante, Prieto Norte tenia el soporte mas suelto; ruta y montaje son factores confundidos.",
              "- La purga usa el centro GPS de ventanas contra fijaciones a ~1 Hz; no certifica independencia de defectos.",
              "- La distancia GPS y su precision son aproximadas. No hay identificadores revisados de baches fisicos.",
              "- Umbral e imputacion se ajustan solo en train; el bosque usa hiperparametros prefijados.",
              "- Los errores FP/FN son contra etiquetas de ventanas, no contra una inspeccion exhaustiva del pavimento.",
              "- No calcular FP/km con negativos muestreados. Falta evaluacion continua y matching uno a uno.",
              "- CAMINO_MALO es una marca puntual: el margen de exclusion no demuestra que todo el tramo este cubierto.",
              "- No elegir NORMAL por amplitud baja; revisar visualmente candidatos y registrar duraciones de tramos.",
              "- Revisar candidatos, sincronizacion y montaje antes de ampliar la campana; reservar rutas nuevas para evaluacion final.",
              "", "## Archivos", "",
              "- audit.json: tiempos, calidad por sensor, conteos y advertencias.",
              "- annotations.csv: todas las marcas, incluidos inicio y fin.",
              "- candidates.csv: pico propuesto, retraso y motivos de exclusion por modo.",
              "- dataset.csv: features, origen de etiquetas, tiempos y GPS.",
              "- metrics.csv: folds y matrices [TN, FP; FN, TP] desglosadas en columnas.",
              "- predictions.csv y errors.csv: predicciones fuera de entrenamiento y errores de ventanas.",
              "- feature_importances.csv: importancias por impureza de cada bosque; no evidencia causal.",
              "- corridor_metrics/predictions/importances.csv: evaluacion manteniendo ida/vuelta juntas, cuando el manifiesto define corredores.",
              "- revision_senales.csv: revision automatica para priorizar inspeccion, sin cambiar etiquetas ni confirmar verdad de terreno.",
              "- senales_*.png: magnitud de aceleracion, contexto temporal y ventana de features sombreada; escalas Y independientes.",
              "- provenance.json: hashes de entradas/codigo, parametros y versiones.",
              "- revision_*.html: senales alrededor de cada anotacion BACHE, para revision manual."]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
