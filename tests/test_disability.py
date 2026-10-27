from decimal import Decimal as D

import pytest

from audiogram.disability import NOT_QUALIFIED, assess, b230_grade, ear_ratio, overall_ratio, to_pta


def test_to_pta_rounds_half_up():
    assert to_pta(46.25) == D("46.3")
    assert to_pta(27.5) == D("27.5")


@pytest.mark.parametrize(
    "pta, expected",
    [(25, "0.0"), (20, "0.0"), (46.3, "32.0"), (27.5, "3.8"), (60, "52.5"), (100, "100.0"), (91.7, "100.0")],
)
def test_ear_ratio(pta, expected):
    assert ear_ratio(pta) == D(expected)


def test_overall_ratio_weights_better_ear_five_to_one():
    assert overall_ratio(ear_ratio(40), ear_ratio(70)) == D("30.0")  # (22.5*5 + 67.5) / 6


@pytest.mark.parametrize(
    "pta_better, pta_worse, grade",
    [
        (60, 60, "b230.1（輕度）"),  # 52.5 %
        (80, 80, "b230.2（中度）"),  # 82.5 %
        (95, 95, "b230.3（重度）"),  # 100 %
        (40, 70, NOT_QUALIFIED),  # 30.0 %
    ],
)
def test_grades(pta_better, pta_worse, grade):
    r = assess(pta_better, pta_worse)
    assert r["grade"] == grade


@pytest.mark.parametrize(
    "overall, grade",
    [
        ("44.9", NOT_QUALIFIED), ("45.0", "b230.1（輕度）"), ("70.0", "b230.1（輕度）"),
        ("70.1", "b230.2（中度）"), ("90.0", "b230.2（中度）"), ("90.1", "b230.3（重度）"),
    ],
)
def test_thresholds_for_six_and_older(overall, grade):
    assert b230_grade(D(overall), D("0"), D("0"), True) == grade


def test_under_six_uses_lower_threshold_and_no_90_48_clause():
    assert b230_grade(D("22.5"), D("30"), D("50"), False) == "b230.1（輕度）"
    assert b230_grade(D("22.5"), D("30"), D("50"), True) == NOT_QUALIFIED
    assert b230_grade(D("22.4"), D("30"), D("50"), False) == NOT_QUALIFIED
    assert b230_grade(D("10"), D("48"), D("90"), False) == NOT_QUALIFIED  # the "or" clause is six-and-older only


def test_ninety_and_forty_eight_clause():
    r = assess(48, 90)
    assert r["overall"] == D("45.0")
    assert r["grade"] == "b230.1（輕度）"
    assert b230_grade(D("10"), D("48"), D("90"), True) == "b230.1（輕度）"


def test_better_ear_is_the_one_with_lower_pta():
    r = assess(50, 30)  # right 50, left 30
    assert (r["better_ear"], r["worse_ear"]) == ("左耳", "右耳")
    assert (r["better_ratio"], r["worse_ratio"]) == (D("7.5"), D("37.5"))
    assert r["overall"] == D("12.5")  # (7.5*5 + 37.5) / 6
    tie = assess(40, 40)
    assert tie["better_ratio"] == tie["worse_ratio"]


def test_missing_ear_cannot_be_assessed():
    r = assess(None, 40)
    assert not r["ok"] and "右耳" in r["reason"]
