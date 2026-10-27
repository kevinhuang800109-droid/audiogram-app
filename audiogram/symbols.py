"""Symbol detection: colour masks + template matching over the plotting area."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .axes import Axes

# Colour decides the ear, shape decides the transducer. Masked symbols (triangle, square, brackets)
# are recorded under the same mode as their unmasked counterpart.
KINDS = {
    "O": ("right", "AC"),
    "^": ("right", "AC"),  # triangle: masked right air conduction
    "<": ("right", "BC"),
    "[": ("right", "BC"),
    "X": ("left", "AC"),
    "#": ("left", "AC"),  # square: masked left air conduction
    ">": ("left", "BC"),
    "]": ("left", "BC"),
}
_COLOUR = {"O": "red", "^": "red", "<": "red", "[": "red", "X": "blue", "#": "blue", ">": "blue", "]": "blue"}
# BC symbols sit beside the frequency line, not on it (right ear to its left, left ear to its right).
_BC_SHIFT = {"right": +0.3, "left": -0.3}  # add shift*size to x to get back to the frequency line
SCALES = (0.7, 0.85, 1.0, 1.15, 1.3)
# Connecting lines score 0.6-0.7 as partial shapes; real symbols score 0.75+. BC symbols are fainter
# (smaller, drawn dotted/overlapped), so they get a lower bar.
THRESHOLD = {"AC": 0.75, "BC": 0.7}
# 750/1.5K/3K/6K are rarely tested, while connecting lines crossing them look like partial symbols.
INTER_OCTAVE = {750, 1500, 3000, 6000}
INTER_OCTAVE_THRESHOLD = 0.85
SYMBOL_PER_OCTAVE = 0.36


@dataclass
class Detection:
    ear: str
    mode: str
    freq: int
    db: float
    score: float
    x: float
    y: float
    kind: str = ""


def colour_masks(img: np.ndarray) -> dict[str, np.ndarray]:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = (((h <= 10) | (h >= 165)) & (s > 70) & (v > 60)).astype(np.float32)
    blue = ((h >= 95) & (h <= 135) & (s > 70) & (v > 60)).astype(np.float32)
    return {"red": red, "blue": blue}


def make_template(kind: str, size: int) -> np.ndarray:
    pad = max(2, size // 6)
    side = (size + 2 * pad) | 1  # odd, so the centre pixel is well defined
    t = np.zeros((side, side), np.uint8)
    thick = max(1, round(size / 9))
    c, r = side // 2, size // 2
    if kind == "O":
        cv2.circle(t, (c, c), r, 255, thick)
    elif kind == "X":
        cv2.line(t, (c - r, c - r), (c + r, c + r), 255, thick)
        cv2.line(t, (c - r, c + r), (c + r, c - r), 255, thick)
    elif kind == "^":
        cv2.polylines(t, [np.array([(c, c - r), (c + r, c + r), (c - r, c + r)])], True, 255, thick)
    elif kind == "#":
        cv2.rectangle(t, (c - r, c - r), (c + r, c + r), 255, thick)
    elif kind == "<":
        cv2.polylines(t, [np.array([(c + r, c - r), (c - r, c), (c + r, c + r)])], False, 255, thick)
    elif kind == ">":
        cv2.polylines(t, [np.array([(c - r, c - r), (c + r, c), (c - r, c + r)])], False, 255, thick)
    elif kind == "[":
        cv2.polylines(t, [np.array([(c + r, c - r), (c - r, c - r), (c - r, c + r), (c + r, c + r)])], False, 255, thick)
    elif kind == "]":
        cv2.polylines(t, [np.array([(c - r, c - r), (c + r, c - r), (c + r, c + r), (c - r, c + r)])], False, 255, thick)
    return (t > 0).astype(np.float32)


_DILATE = np.ones((3, 3), np.uint8)


def match_score(mask01: np.ndarray, tpl: np.ndarray) -> np.ndarray:
    """coverage x precision of `tpl` at every position of `mask01`.

    coverage  = share of template pixels present in the mask (lines through the symbol don't hurt),
    precision = share of mask pixels in the template window that the template explains
                (rejects, e.g., one half of an X being taken for a '>').
    """
    side = tpl.shape[0]
    cover = cv2.matchTemplate(cv2.dilate(mask01, _DILATE), tpl, cv2.TM_CCORR) / tpl.sum()
    inside = cv2.matchTemplate(mask01, cv2.dilate(tpl, _DILATE), cv2.TM_CCORR)
    total = cv2.boxFilter(mask01, -1, (side, side), normalize=False)
    r = side // 2
    total = total[r:r + cover.shape[0], r:r + cover.shape[1]]
    return cover * (inside / np.maximum(total, 1.0))


def _peaks(resp: np.ndarray, radius: int, threshold: float, limit: int = 30) -> list[tuple[float, int, int]]:
    resp = resp.copy()
    out = []
    for _ in range(limit):
        _, mx, _, loc = cv2.minMaxLoc(resp)
        if mx < threshold:
            break
        out.append((mx, loc[0], loc[1]))
        x, y = loc
        resp[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1] = -1
    return out


def detect_symbols(img: np.ndarray, axes: Axes, symbol_px: int | None = None) -> list[Detection]:
    h, w = img.shape[:2]
    x0, y0, x1, y1 = axes.plot_box()
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    masks = {k: m[y0:y1, x0:x1] for k, m in colour_masks(img).items()}
    base = symbol_px or max(8, int(axes.octave_px * SYMBOL_PER_OCTAVE))

    cands: list[tuple[float, str, float, float, int]] = []  # score, kind, x, y, size
    for kind, colour in _COLOUR.items():
        for scale in SCALES:
            size = max(7, int(base * scale))
            tpl = make_template(kind, size)
            if masks[colour].shape[0] < tpl.shape[0] or masks[colour].shape[1] < tpl.shape[1]:
                continue
            for score, px, py in _peaks(match_score(masks[colour], tpl), size // 2, min(THRESHOLD.values())):
                cands.append((score, kind, px + tpl.shape[1] // 2 + x0, py + tpl.shape[0] // 2 + y0, size))

    # non-maximum suppression within one ear (colour); different ears may legitimately overlap
    cands.sort(reverse=True)
    kept: list[tuple[float, str, float, float, int]] = []
    for c in cands:
        if all(_COLOUR[c[1]] != _COLOUR[k[1]] or np.hypot(c[2] - k[2], c[3] - k[3]) > 0.7 * max(c[4], k[4]) for k in kept):
            kept.append(c)

    columns = axes.columns
    detections = []
    # On a score tie, the plain symbols (O, X) beat the masked ones: a triangle is often just a circle's top edge.
    kept.sort(key=lambda c: (c[0] + (0.001 if c[1] in "OX" else 0)), reverse=True)
    for score, kind, x, y, size in kept:
        ear, mode = KINDS[kind]
        # Thresholds apply only after suppression, so a weak circle still shadows the '<' that is half of it.
        if score < THRESHOLD[mode]:
            continue
        if mode == "BC":
            x += _BC_SHIFT[ear] * size
        freq, cx = min(columns, key=lambda c: abs(c[1] - x))
        if freq in INTER_OCTAVE and score < INTER_OCTAVE_THRESHOLD:
            continue
        db = round(axes.y_to_db(y) / 5) * 5
        detections.append(Detection(ear, mode, freq, float(db), float(score), x, y, kind))
    return detections
