"""Hearing-disability ratio and b230 grade (身心障礙者鑑定作業辦法, as given by the user).

PTA   = mean of 500/1000/2000/4000 Hz air-conduction thresholds, per ear, rounded to 0.1 dB
ear   = (PTA - 25) x 1.5 %, capped at 100 %, 0 % at or below 25 dB
total = (better-ear ratio x 5 + worse-ear ratio x 1) / 6
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_TENTH = Decimal("0.1")
GRADES = {1: "b230.1（輕度）", 2: "b230.2（中度）", 3: "b230.3（重度）"}
NOT_QUALIFIED = "未達鑑定標準"


def _round1(value: Decimal) -> Decimal:
    return value.quantize(_TENTH, rounding=ROUND_HALF_UP)


def to_pta(average: float) -> Decimal:
    """A four-frequency average rounded to one decimal, half up (46.25 -> 46.3)."""
    return _round1(Decimal(repr(average)))


def ear_ratio(pta) -> Decimal:
    """Single-ear hearing-loss ratio in percent, to one decimal."""
    ratio = (Decimal(str(pta)) - 25) * Decimal("1.5")
    return _round1(max(Decimal(0), min(Decimal(100), ratio)))


def overall_ratio(better: Decimal, worse: Decimal) -> Decimal:
    """Both-ear overall ratio from the two (already rounded) single-ear ratios."""
    return _round1((better * 5 + worse) / 6)


def b230_grade(overall: Decimal, better_pta: Decimal, worse_pta: Decimal, six_or_older: bool) -> str:
    if overall >= Decimal("90.1"):
        return GRADES[3]
    if overall >= Decimal("70.1"):
        return GRADES[2]
    if six_or_older:
        # 45.0-70.0 %, or one ear >= 90 dB with the other >= 48 dB
        if overall >= Decimal("45.0") or (worse_pta >= 90 and better_pta >= 48):
            return GRADES[1]
    elif overall >= Decimal("22.5"):  # under six: 22.5-70.0 %
        return GRADES[1]
    return NOT_QUALIFIED


def assess(pta_right: float | None, pta_left: float | None, six_or_older: bool = True) -> dict:
    """Everything the page shows. `ok` is False when either ear has no four-frequency average."""
    if pta_right is None or pta_left is None:
        missing = [name for name, v in (("右耳", pta_right), ("左耳", pta_left)) if v is None]
        return {"ok": False, "reason": f"需要左右耳氣導 500/1000/2000/4000 Hz 都有數值才能計算（目前缺：{'、'.join(missing)}）"}
    ears = {"右耳": to_pta(pta_right), "左耳": to_pta(pta_left)}
    better, worse = sorted(ears, key=lambda e: ears[e])  # stable: the right ear is "better" on a tie
    ratios = {e: ear_ratio(ears[e]) for e in ears}
    overall = overall_ratio(ratios[better], ratios[worse])
    return {
        "ok": True,
        "better_ear": better, "worse_ear": worse,
        "better_pta": ears[better], "worse_pta": ears[worse],
        "better_ratio": ratios[better], "worse_ratio": ratios[worse],
        "overall": overall,
        "grade": b230_grade(overall, ears[better], ears[worse], six_or_older),
    }
