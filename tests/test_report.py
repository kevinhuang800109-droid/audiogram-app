from audiogram.calc import FREQS
from audiogram.report import build_report, round_half_up


def _th(**rows):
    out = {(e, m): {f: None for f in FREQS} for e in ("right", "left") for m in ("AC", "BC")}
    for name, values in rows.items():
        ear, mode = name.split("_")
        out[(ear, mode)].update(values)
    return out


def test_round_half_up():
    assert round_half_up(36.25) == "36.3"
    assert round_half_up(27.5) == "27.5"
    assert round_half_up(20.0) == "20.0"


def test_full_report():
    th = _th(
        right_AC={250: 45, 500: 50, 1000: 50, 2000: 40, 4000: 45, 8000: 40},
        left_AC={250: 20, 500: 20, 1000: 30, 2000: 40, 4000: 55, 8000: 70},
        right_BC={500: 0, 1000: 5, 2000: 15, 4000: 30},  # BC never gets its own row
    )
    report = build_report(th, ["SDT : R't 80dBHL ; L't 70dBHL", "  "], "BO(insert earphone)\nMRL=R't 85dBHL")
    assert report == (
        "Rt 45-50-50-40-45-40\n"
        "Lt 20-20-30-40-55-70\n"
        "4-frequency average (500/1000/2000/4000 Hz): Rt AC 46.3 dB, Lt AC 36.3 dB, Rt BC 12.5 dB\n"
        "\n"
        "Tymp / SRT / SRS\n"
        "SDT : R't 80dBHL ; L't 70dBHL\n"
        "\n"
        "Comments\n"
        "BO(insert earphone)\nMRL=R't 85dBHL"
    )


def test_missing_frequency_shows_question_mark_and_no_average():
    th = _th(right_AC={500: 20, 1000: 30, 2000: 40})  # no 250 / 4000 / 8000
    assert build_report(th, [], "") == "Rt ?-20-30-40-?-?"


def test_negative_threshold_and_empty_ear_omitted():
    th = _th(right_AC={250: 5, 500: 5, 1000: 5, 2000: 0, 4000: 0, 8000: -5})
    assert build_report(th, [], "").splitlines()[0] == "Rt 5-5-5-0-0--5"
    assert "Lt" not in build_report(th, [], "")


def test_bc_average_listed_when_complete():
    th = _th(right_BC={500: 0, 1000: 5, 2000: 15, 4000: 30})
    assert build_report(th, [], "") == "4-frequency average (500/1000/2000/4000 Hz): Rt BC 12.5 dB"
