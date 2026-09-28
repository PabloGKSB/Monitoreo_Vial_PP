"""Signal-review triage, never automatic relabeling or ground-truth validation."""

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from .data import PilotConfig, PilotTrip


def review_rows(dataset: pd.DataFrame, candidates: pd.DataFrame, config: PilotConfig) -> pd.DataFrame:
    # Use one mode: the NORMAL windows are shared and positives must not be counted twice.
    data = dataset[dataset["mode"] == "peak_assisted"].copy()
    marks = candidates.set_index(["route_id", "annotation_id"])
    rows = []
    for route, part in data.groupby("route_id"):
        positive_q25 = part.loc[part.label == 1, "acc_mag_absmax"].quantile(.25)
        for row in part.itertuples():
            flags = []
            delay = np.nan
            if row.label:
                mark = marks.loc[(route, row.annotation_id)]
                delay = float(mark.candidate_delay_seconds)
                if abs(delay) <= .25:
                    flags.append("PEAK_NEAR_BUTTON")
                if delay < 0:
                    flags.append("PEAK_AFTER_BUTTON")
                if (delay >= config.search_before_seconds - .15
                        or delay <= -config.search_after_seconds + .15):
                    flags.append("PEAK_NEAR_SEARCH_EDGE")
                if abs(delay - config.fixed_delay_seconds) > config.window_seconds / 2:
                    flags.append("PEAK_OUTSIDE_FIXED_WINDOW")
            elif row.acc_mag_absmax >= positive_q25:
                flags.append("AMPLITUDE_OVERLAPS_BACHE_Q25")
            rows.append({"sample_id": row.sample_id, "route_id": route,
                         "annotation_id": row.annotation_id, "original_label": row.label,
                         "center_seconds": row.seconds_elapsed,
                         "annotation_seconds": row.annotation_seconds,
                         "candidate_delay_seconds": delay,
                         "acc_peak_m_s2": row.acc_mag_absmax, "acc_rms_m_s2": row.acc_mag_rms,
                         "gyro_peak_rad_s": row.gyro_mag_absmax, "speed_kmh": row.speed_kmh,
                         "route_bache_peak_q25": positive_q25,
                         "triage_flags": "|".join(flags) or "NO_HEURISTIC_FLAG",
                         "ground_truth_status": "UNVERIFIED",
                         "review_decision": "", "review_notes": ""})
    return pd.DataFrame(rows)


def save_contact_sheets(trips: list[PilotTrip], review: pd.DataFrame, output: Path,
                        config: PilotConfig) -> None:
    """Actual native-sample acceleration magnitude, independent y scale per panel."""
    for trip in trips:
        signal = trip.signals["accelerometer"]
        t = signal.seconds_elapsed.to_numpy(float)
        mag = np.linalg.norm(signal[["x", "y", "z"]].to_numpy(float), axis=1)
        for label, part in review[review.route_id == trip.route_id].groupby("original_label"):
            kind = "BACHE" if label else "NORMAL"
            for page, offset in enumerate(range(0, len(part), 20), 1):
                page_rows = part.iloc[offset:offset + 20]
                sheet = Image.new("RGB", (1600, 80 + 255 * int(np.ceil(len(page_rows) / 4))), "white")
                draw = ImageDraw.Draw(sheet)
                draw.text((15, 10), f"{trip.route_id} / {kind} / {page} | acc magnitude (m/s2); independent Y scales", fill="black")
                draw.text((15, 30), "Blue=signal; red=button; green=window center; gray=feature window; NOT confirmed labels", fill="black")
                for index, row in enumerate(page_rows.itertuples()):
                    x0, y0 = 15 + (index % 4) * 400, 65 + (index // 4) * 255
                    center = row.annotation_seconds if label else row.center_seconds
                    left, right = (center - 4, center + 2) if label else (center - 3, center + 3)
                    mask = (t >= left) & (t <= right)
                    ts, ys = t[mask], mag[mask]
                    ymax = max(float(ys.max()), .1) * 1.05
                    plot_x, plot_y, width, height = x0 + 25, y0 + 60, 340, 140
                    draw.text((x0, y0), str(row.annotation_id) if label else row.sample_id.split("_")[-1], fill="black")
                    draw.text((x0, y0 + 16), f"t={center:.2f}s peak={row.acc_peak_m_s2:.2f} gyro={row.gyro_peak_rad_s:.2f}", fill="black")
                    draw.text((x0, y0 + 32), f"delay={row.candidate_delay_seconds:.2f}s speed={row.speed_kmh:.1f}km/h", fill="black")
                    draw.text((x0, plot_y), f"{ymax:.1f}", fill="black")
                    half = config.window_seconds / 2
                    window_left = plot_x + max(0, (row.center_seconds-half-left)/(right-left))*width
                    window_right = plot_x + min(1, (row.center_seconds+half-left)/(right-left))*width
                    draw.rectangle((window_left, plot_y, window_right, plot_y+height), fill="#eeeeee")
                    draw.line((plot_x, plot_y, plot_x, plot_y + height, plot_x + width, plot_y + height), fill="#aaaaaa")
                    points = [(plot_x + (x-left)/(right-left)*width, plot_y+height-y/ymax*height) for x, y in zip(ts, ys)]
                    draw.line(points, fill="#1264a3", width=1)
                    for instant, color in ((center, "#cf3131"), (row.center_seconds, "#228844")):
                        pos = plot_x + (instant-left)/(right-left)*width
                        draw.line((pos, plot_y, pos, plot_y + height), fill=color, width=1)
                    for instant, label_text in ((left, f"{left-center:+.0f}s"), (center, "0"), (right, f"{right-center:+.0f}s")):
                        pos = plot_x + (instant-left)/(right-left)*width
                        draw.text((pos, plot_y + height + 5), label_text, fill="black", anchor="mt")
                    draw.text((x0, y0 + 225), row.triage_flags[:53], fill="black")
                sheet.save(output / f"senales_{trip.route_id}_{kind}_{page}.png")


def write_review(trips: list[PilotTrip], dataset: pd.DataFrame, candidates: pd.DataFrame,
                 config: PilotConfig, output: Path) -> pd.DataFrame:
    review = review_rows(dataset, candidates, config)
    review.to_csv(output / "revision_senales.csv", index=False)
    save_contact_sheets(trips, review, output, config)
    return review
