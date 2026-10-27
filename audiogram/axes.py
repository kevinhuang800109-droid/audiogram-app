"""Axis calibration from OCR'd tick labels (no dependence on grid-line detection)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import cv2
import numpy as np
import pytesseract

_DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = os.environ.get(
    "TESSERACT_CMD", _DEFAULT_TESSERACT if os.path.exists(_DEFAULT_TESSERACT) else "tesseract"
)

STD_FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 12000]
DB_MIN, DB_MAX = -10, 120
# Labels as printed -> Hz. Small images lose the '.' in "1.5K", so "15K" is accepted too.
_LABELS = {"125": 125, "250": 250, "500": 500, "750": 750, "1K": 1000, "1.5K": 1500, "15K": 1500,
           "2K": 2000, "3K": 3000, "4K": 4000, "6K": 6000, "8K": 8000, "12K": 12000}


@dataclass
class Axes:
    freq_a: float  # x = freq_a * log2(Hz) + freq_b
    freq_b: float
    db_a: float  # y = db_a * dB + db_b
    db_b: float
    notes: list[str] = field(default_factory=list)

    @property
    def octave_px(self) -> float:
        return abs(self.freq_a)

    @property
    def columns(self) -> list[tuple[int, float]]:
        return [(f, self.freq_a * np.log2(f) + self.freq_b) for f in STD_FREQS]

    def y_to_db(self, y: float) -> float:
        return (y - self.db_b) / self.db_a

    def db_to_y(self, db: float) -> float:
        return self.db_a * db + self.db_b

    def plot_box(self) -> tuple[int, int, int, int]:
        """x0, y0, x1, y1 of the plotting area (125..12000 Hz, -10..120 dB), padded by half a symbol."""
        xs = [x for _, x in self.columns]
        pad = 0.2 * self.octave_px
        return int(min(xs) - pad), int(self.db_to_y(DB_MIN) - pad), int(max(xs) + pad), int(self.db_to_y(DB_MAX) + pad)


def _ocr_tokens(img: np.ndarray, scale: int) -> list[tuple[str, float, float]]:
    big = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    d = pytesseract.image_to_data(big, config="--psm 11", output_type=pytesseract.Output.DICT)
    return [
        (t.strip(), (x + w / 2) / scale, (y + h / 2) / scale)
        for t, x, y, w, h in zip(d["text"], d["left"], d["top"], d["width"], d["height"])
        if t.strip()
    ]


def _parse_freq(text: str) -> int | None:
    t = re.sub(r"[^0-9A-Za-z.]", "", text).upper().replace("S", "5").replace("O", "0").replace("I", "1").replace("L", "1")
    return _LABELS.get(t)


def _parse_db(text: str) -> int | None:
    m = re.fullmatch(r"[^\d-]?(-?)\s*(\d{1,3})", text)
    if not m:
        return None
    v = int(m.group(2)) * (-1 if m.group(1) else 1)
    return v if DB_MIN <= v <= DB_MAX and v % 10 == 0 else None


def _robust_line(pts: list[tuple[float, float]], tol: float) -> tuple[float, float] | None:
    """Least-squares y = a*x + b on (x, y) pairs, repeatedly dropping the worst outlier beyond `tol`."""
    pts = list(pts)
    while len({p[0] for p in pts}) >= 2:
        a, b = np.polyfit([p[0] for p in pts], [p[1] for p in pts], 1)
        res = [abs(a * x + b - y) for x, y in pts]
        worst = int(np.argmax(res))
        if res[worst] <= tol:
            return float(a), float(b)
        if len(pts) <= 2:
            return None
        pts.pop(worst)
    return None


def calibrate(img: np.ndarray) -> Axes:
    h, w = img.shape[:2]
    tokens: list[tuple[str, float, float]] = []
    base = int(np.clip(round(1500 / w), 3, 6))
    for scale in (base, base + 1):
        tokens += _ocr_tokens(img, scale)

    # --- frequency axis: x = a*log2(Hz) + b, anchors from the labels above / below the plot ---
    anchors: dict[int, list[float]] = {}
    for text, cx, cy in tokens:
        hz = _parse_freq(text)
        if hz and (cy < 0.25 * h or cy > 0.5 * h):
            anchors.setdefault(hz, []).append(cx)
    pts = [(np.log2(hz), float(np.median(xs))) for hz, xs in anchors.items()]
    fit = _robust_line(pts, tol=0.03 * w)  # coarse first pass; tightened below once the octave size is known
    if fit is None or fit[0] <= 0:
        raise ValueError("讀不到足夠的頻率刻度文字(125/250/500/1K…)，無法校準橫軸")
    fa, fb = fit
    fit = _robust_line(pts, tol=0.25 * fa)
    if fit is None:
        raise ValueError("頻率刻度文字互相矛盾，無法校準橫軸")
    fa, fb = fit

    # --- dB axis: y = a*dB + b, anchors from the label column left of the 125 Hz line ---
    x_limit = min(fa * lg + fb for lg, _ in pts) - 5  # left of the leftmost frequency label
    cand = [(_parse_db(t), cy) for t, cx, cy in tokens if cx < x_limit and 0.05 * h < cy < 0.95 * h]
    cand = [(v, y) for v, y in cand if v is not None]
    sure = [(v, y) for v, y in cand if v >= 20]
    init = _robust_line(sure, tol=6) if len({v for v, _ in sure}) >= 2 else None
    if init is None:
        raise ValueError("讀不到足夠的 dB 刻度文字，無法校準縱軸")
    a, b = init
    pts = list(sure)
    for v, y in cand:
        if v < 20:  # +-10 and 0 are ambiguous after OCR ("10" may be "-10"): take the sign that fits
            v = min((v, -v), key=lambda c: abs(a * c + b - y))
            pts.append((v, y))
    fit = _robust_line(pts, tol=0.4 * abs(a) * 10)
    a, b = fit if fit else init
    return Axes(fa, fb, a, b)
