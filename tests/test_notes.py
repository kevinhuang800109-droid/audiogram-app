from audiogram.notes import _keyword, extract_comments, extract_notes, fix_digits
from tools.make_synthetic import render

LINES = [
    "Tymp Rt type A Lt type B",
    "SRT Rt 20 dB Lt 25 dB",
    "SRS Rt 96% 60 dB Lt 92% 65 dB",
]


def test_keyword_tolerates_ocr_confusions():
    assert _keyword("SRI") == "SRT"
    assert _keyword("SDT") == "SRT"
    assert _keyword("SDI:") == "SRT"
    assert _keyword("SR5:") == "SRS"
    assert _keyword("Tympanogram") == "Tympanogram"
    assert _keyword("Frequency") is None


def test_fix_digits_only_before_units():
    assert fix_digits("MRL=R't 8SdBHL ; L't 80-8SdBHL") == "MRL=R't 85dBHL ; L't 80-85dBHL"
    assert fix_digits("SDT : R't 8OdBHL ; L't 7OdBHL") == "SDT : R't 80dBHL ; L't 70dBHL"
    assert fix_digits("tymp(1OO0Hz) 9S%") == "tymp(1000Hz) 95%"
    # a leading S could be an 8 or a 5: don't guess
    assert fix_digits("R't SOdBHL") == "R't SOdBHL"
    # words and numbers without a unit are left alone
    assert fix_digits("SOS Rt Oslo type B ; O dBA") == "SOS Rt Oslo type B ; O dBA"


def test_copies_text_verbatim():
    notes = extract_notes(render(notes=LINES))
    assert {n.kind: n.text for n in notes} == {
        "Tympanogram": LINES[0],
        "SRT": LINES[1],
        "SRS": LINES[2],
    }


def test_sdt_is_treated_as_srt():
    notes = extract_notes(render(notes=["SDT Rt 20 dB Lt 25 dB"]))
    assert [(n.kind, n.text) for n in notes] == [("SRT", "SDT Rt 20 dB Lt 25 dB")]


def test_comments_copies_everything_below_heading():
    body = ["PTA Rt 15 dB Lt 40 dB", "SDT Rt 20 dB Lt 25 dB", "Tymp Rt type A Lt type B", "Good reliability."]
    c = extract_comments(render(notes=["Comments:"] + body))
    assert c is not None and c.kind == "Comments"
    assert c.text == "\n".join(body)


def test_comments_absent():
    assert extract_comments(render()) is None


def test_no_notes_on_plain_chart():
    assert extract_notes(render()) == []
