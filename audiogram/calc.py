"""Threshold bookkeeping and the four-frequency average."""
from __future__ import annotations

FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 12000]
AVG_FREQS = [500, 1000, 2000, 4000]
EARS = ["right", "left"]
MODES = ["AC", "BC"]


def four_freq_average(thresholds: dict[int, float | None]) -> float | None:
    """Mean of the 500/1000/2000/4000 Hz thresholds, or None if any is missing."""
    values = [thresholds.get(f) for f in AVG_FREQS]
    if any(v is None for v in values):
        return None
    return sum(values) / len(values)


def empty_result() -> dict[tuple[str, str], dict[int, float | None]]:
    return {(ear, mode): {f: None for f in FREQS} for ear in EARS for mode in MODES}
