"""End-to-end analysis: image bytes -> thresholds, averages, overlay."""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .axes import DB_MAX, DB_MIN, Axes, calibrate
from .calc import empty_result, four_freq_average
from .notes import Note, extract_comments, extract_notes
from .preprocess import load_image
from .symbols import Detection, detect_symbols


@dataclass
class Analysis:
    thresholds: dict[tuple[str, str], dict[int, float | None]]
    detections: list[Detection]
    axes: Axes
    overlay: np.ndarray
    notes: list[Note] = field(default_factory=list)
    image: np.ndarray | None = None
    comments: Note | None = None

    def averages(self) -> dict[tuple[str, str], float | None]:
        return {key: four_freq_average(th) for key, th in self.thresholds.items()}


def analyze(data: bytes) -> Analysis:
    img = load_image(data)
    axes = calibrate(img)
    detections = detect_symbols(img, axes)

    thresholds = empty_result()
    for d in detections:  # already ordered best first; keep the first one per slot
        if thresholds[(d.ear, d.mode)][d.freq] is None:
            thresholds[(d.ear, d.mode)][d.freq] = d.db

    overlay = img.copy()
    columns = axes.columns
    top, bottom = int(axes.db_to_y(DB_MIN)), int(axes.db_to_y(DB_MAX))
    for _, x in columns:
        cv2.line(overlay, (int(x), top), (int(x), bottom), (0, 200, 0), 1)
    left, right = int(columns[0][1]), int(columns[-1][1])
    for db in range(DB_MIN, DB_MAX + 1, 10):
        y = int(axes.db_to_y(db))
        cv2.line(overlay, (left, y), (right, y), (0, 200, 0), 1)
    for d in detections:
        cv2.circle(overlay, (int(d.x), int(d.y)), 3, (0, 160, 255), -1)
        cv2.putText(overlay, f"{d.db:g}", (int(d.x) + 5, int(d.y) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 120, 0), 1, cv2.LINE_AA)
    try:
        notes = extract_notes(img)
    except Exception:  # the free-text copy is a bonus; never let it break the threshold analysis
        notes = []
    try:
        comments = extract_comments(img)
    except Exception:
        comments = None
    return Analysis(thresholds, detections, axes, overlay, notes, img, comments)
