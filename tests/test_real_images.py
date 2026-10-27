"""Regression on real audiograms (values read off the charts by eye). Air conduction only."""
from pathlib import Path

import pytest

from audiogram.pipeline import analyze

ROOT = Path(__file__).resolve().parents[1]
F = [250, 500, 1000, 2000, 4000, 8000]
CASES = {
    "圖片1.png": ([15, 5, 10, 0, 5, 5], [45, 35, 40, 35, 45, 60]),
    "圖片2.png": ([10, 5, 5, 0, 5, 0], [35, 35, 40, 40, 55, 50]),
    "圖片5.png": ([45, 50, 50, 40, 45, 40], [20, 15, 15, 15, 10, 0]),
}


@pytest.mark.parametrize("name", CASES)
def test_air_conduction(name):
    path = ROOT / name
    if not path.exists():
        pytest.skip(f"{name} not present")
    result = analyze(path.read_bytes())
    right, left = CASES[name]
    for ear, expected in (("right", right), ("left", left)):
        got = [result.thresholds[(ear, "AC")][f] for f in F]
        assert got == [float(v) for v in expected], ear
