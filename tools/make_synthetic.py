"""Render a synthetic audiogram with known thresholds, for pipeline checks."""
from __future__ import annotations

import json
import sys

import cv2
import numpy as np

FREQS = [250, 500, 1000, 2000, 4000, 8000]
RED, BLUE = (0, 0, 220), (220, 60, 0)  # BGR
X0, X1, Y0, STEP_X, STEP_Y = 110, 460, 90, 70, 40

TRUTH = {
    "right_AC": {250: 10, 500: 15, 1000: 20, 2000: 30, 4000: 45, 8000: 60},
    "left_AC": {250: 15, 500: 20, 1000: 30, 2000: 40, 4000: 55, 8000: 70},
    "right_BC": {500: 0, 1000: 5, 2000: 15, 4000: 30},
    "left_BC": {500: 5, 1000: 15, 2000: 25, 4000: 35},
}


def _x(f: int) -> int:
    return X0 + FREQS.index(f) * STEP_X


def _y(db: float) -> int:
    return int(Y0 + (db + 10) / 10 * STEP_Y)


def _symbol(img, kind, x, y, colour, r=12):
    if kind == "O":
        cv2.circle(img, (x, y), r, colour, 2, cv2.LINE_AA)
    elif kind == "X":
        cv2.line(img, (x - r, y - r), (x + r, y + r), colour, 2, cv2.LINE_AA)
        cv2.line(img, (x - r, y + r), (x + r, y - r), colour, 2, cv2.LINE_AA)
    elif kind == "<":
        cv2.polylines(img, [np.array([(x + r, y - r), (x - r, y), (x + r, y + r)])], False, colour, 2, cv2.LINE_AA)
    elif kind == ">":
        cv2.polylines(img, [np.array([(x - r, y - r), (x + r, y), (x - r, y + r)])], False, colour, 2, cv2.LINE_AA)


def render(truth=TRUTH, notes=()) -> np.ndarray:
    img = np.full((700 + 30 * len(notes), 560, 3), 255, np.uint8)
    for i, line in enumerate(notes):
        cv2.putText(img, line, (20, 665 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    y_end = _y(120)
    for db in range(-10, 130, 10):
        cv2.line(img, (X0, _y(db)), (X1, _y(db)), (150, 150, 150), 1)
        cv2.putText(img, str(db), (X0 - 50, _y(db) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    for f in FREQS:
        cv2.line(img, (_x(f), Y0), (_x(f), y_end), (150, 150, 150), 1)
        cv2.putText(img, str(f), (_x(f) - 18, Y0 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    for key, colour, ac_kind, bc_kind in (("right", RED, "O", "<"), ("left", BLUE, "X", ">")):
        ac = truth[f"{key}_AC"]
        pts = np.array([(_x(f), _y(db)) for f, db in ac.items()])
        cv2.polylines(img, [pts], False, colour, 2, cv2.LINE_AA)
        for f, db in ac.items():
            _symbol(img, ac_kind, _x(f), _y(db), colour)
        for f, db in truth[f"{key}_BC"].items():
            _symbol(img, bc_kind, _x(f), _y(db), colour)
    return img


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "synthetic.png"
    ok, buf = cv2.imencode(".png", render())
    buf.tofile(out)
    with open(out + ".json", "w", encoding="utf-8") as fh:
        json.dump(TRUTH, fh)
    print("wrote", out)
