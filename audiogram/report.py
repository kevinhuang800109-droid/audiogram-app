"""Plain-text report built from the (possibly hand-corrected) thresholds and copied text."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .calc import AVG_FREQS, four_freq_average

REPORT_FREQS = [250, 500, 1000, 2000, 4000, 8000]
_NAMES = {("right", "AC"): "Rt AC", ("left", "AC"): "Lt AC", ("right", "BC"): "Rt BC", ("left", "BC"): "Lt BC"}


def round_half_up(value: float, places: int = 1) -> str:
    """36.25 -> "36.3" (Python's own formatting would give 36.2)."""
    q = Decimal(1).scaleb(-places)
    return str(Decimal(repr(value)).quantize(q, rounding=ROUND_HALF_UP))


def build_report(
    thresholds: dict[tuple[str, str], dict[int, float | None]],
    notes: list[str],
    comments: str,
) -> str:
    blocks: list[str] = []

    lines = []
    for ear, name in (("right", "Rt"), ("left", "Lt")):
        # six air-conduction values, 250 -> 8000 Hz, joined by "-"; a frequency with no reading shows "?"
        ac = thresholds.get((ear, "AC"), {})
        if any(ac.get(f) is not None for f in REPORT_FREQS):
            lines.append(f"{name} " + "-".join("?" if ac.get(f) is None else f"{ac[f]:g}" for f in REPORT_FREQS))
    averages = []
    for key, name in _NAMES.items():
        avg = four_freq_average(thresholds.get(key, {}))
        if avg is not None:
            averages.append(f"{name} {round_half_up(avg)} dB")
    if averages:
        lines.append(f"4-frequency average ({'/'.join(map(str, AVG_FREQS))} Hz): {', '.join(averages)}")
    if lines:
        blocks.append("\n".join(lines))

    notes = [n.strip() for n in notes if n.strip()]
    if notes:
        blocks.append("Tymp / SRT / SRS\n" + "\n".join(notes))
    if comments.strip():
        blocks.append("Comments\n" + comments.strip())
    return "\n\n".join(blocks)
