import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audiogram.pipeline import analyze
from tools.make_synthetic import TRUTH, render


def test_synthetic_audiogram_roundtrip():
    ok, buf = cv2.imencode(".png", render())
    result = analyze(buf.tobytes())
    for name, expected in TRUTH.items():
        ear, mode = name.split("_")
        got = {f: v for f, v in result.thresholds[(ear, mode)].items() if v is not None}
        assert got == {f: float(v) for f, v in expected.items()}, name
    assert result.averages()[("right", "AC")] == (15 + 20 + 30 + 45) / 4
    assert result.averages()[("left", "AC")] == (20 + 30 + 40 + 55) / 4
