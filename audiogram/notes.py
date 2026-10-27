"""Copy out the Tympanogram / SRT / SRS text printed on an audiogram. No interpretation, just OCR."""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract

from . import axes as _axes  # noqa: F401  (configures the tesseract path)

KINDS = ("Tympanogram", "SRT", "SRS")

# OCR reads the digits 0/5/1 as the letters O/S/I next to a dB value ("8SdBHL" -> "85dBHL").
# A leading "S" is ambiguous (an OCR'd 8 or 5?), so a number may not start with S: "SOdBHL" is left as read.
_NUM_WITH_UNIT = re.compile(r"(?<![A-Za-z0-9])([0-9OoIl][0-9OoSIl\-]*)(?=(?:dB|Hz|HZ|%))")
_LETTER_TO_DIGIT = str.maketrans({"O": "0", "o": "0", "S": "5", "I": "1", "l": "1"})


def fix_digits(text: str) -> str:
    """Repair letters standing where a digit must be, only in a number directly followed by dB, Hz or %."""
    return _NUM_WITH_UNIT.sub(lambda m: m.group(1).translate(_LETTER_TO_DIGIT), text)


@dataclass
class Note:
    kind: str  # "Tympanogram" | "SRT" | "SRS"
    text: str  # verbatim OCR text, keyword first
    box: tuple[int, int, int, int]  # x0, y0, x1, y1 in original image pixels

    def crop(self, img: np.ndarray, margin: int = 6) -> np.ndarray:
        x0, y0, x1, y1 = self.box
        h, w = img.shape[:2]
        return img[max(0, y0 - margin):min(h, y1 + margin), max(0, x0 - margin):min(w, x1 + margin)]


def _keyword(token: str) -> str | None:
    t = re.sub(r"[^0-9A-Za-z]", "", token).lower()
    if len(t) < 3:
        return None
    # SDT is the same test as SRT. OCR confuses T/I/1/l and S/5 at the end of "SRT" / "SRS"
    if re.fullmatch(r"s[rd][t1il]", t):
        return "SRT"
    if re.fullmatch(r"sr[s5]", t):
        return "SRS"
    if t.startswith("tymp") or (len(t) >= 4 and difflib.SequenceMatcher(None, t, "tympanogram"[:len(t)]).ratio() >= 0.8):
        return "Tympanogram"
    return None


def _lines(img: np.ndarray) -> list[list[tuple[str, int, int, int, int]]]:
    """OCR lines as lists of (text, x0, y0, x1, y1) in original pixels, top to bottom."""
    h, w = img.shape[:2]
    scale = float(np.clip(1500 / w, 2, 5))
    big = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    d = pytesseract.image_to_data(big, config="--psm 6", output_type=pytesseract.Output.DICT)
    groups: dict[tuple[int, int, int], list[tuple[str, int, int, int, int]]] = {}
    for i, text in enumerate(d["text"]):
        if not text.strip() or float(d["conf"][i]) < 0:
            continue
        x, y, bw, bh = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        box = (int(x / scale), int(y / scale), int((x + bw) / scale), int((y + bh) / scale))
        groups.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append((text.strip(), *box))
    lines = [sorted(g, key=lambda t: t[1]) for g in groups.values()]
    return sorted(lines, key=lambda g: min(t[2] for t in g))


def _is_comments(token: str) -> bool:
    t = re.sub(r"[^A-Za-z]", "", token).lower()
    return len(t) >= 6 and (t.startswith("comment") or difflib.SequenceMatcher(None, t, "comments").ratio() >= 0.85)


def _join(line: list[tuple[str, int, int, int, int]]) -> str:
    """Words of one OCR line; a wide gap (a column break) becomes two spaces."""
    out = line[0][0]
    for prev, cur in zip(line, line[1:]):
        gap = cur[1] - prev[3]
        out += ("  " if gap > 2 * (cur[4] - cur[2]) else " ") + cur[0]
    return out


def extract_comments(img: np.ndarray) -> Note | None:
    """Everything printed below the "Comments" heading (plus anything after it on its own line), as text."""
    h, w = img.shape[:2]
    for line in _lines(img):
        idx = next((i for i, t in enumerate(line) if _is_comments(t[0])), None)
        if idx is None:
            continue
        head = line[idx + 1:]
        y_below = max(t[4] for t in line)
        # Re-read the region below the heading on its own: cleaner than lines cut out of the full-page pass.
        below = img[min(h - 1, y_below + 1):, :]
        body = [_join(g) for g in _lines(below)] if below.shape[0] > 8 else []
        parts = ([_join(head)] if head else []) + body
        if not parts:
            return None
        x0 = min(t[1] for t in line)
        return Note("Comments", fix_digits("\n".join(parts)), (x0, line[0][2], w, h))
    return None


def extract_notes(img: np.ndarray) -> list[Note]:
    notes: list[Note] = []
    lines = _lines(img)
    for line in lines:
        starts = [i for i, t in enumerate(line) if _keyword(t[0])]
        for n, start in enumerate(starts):
            end = starts[n + 1] if n + 1 < len(starts) else len(line)
            words = line[start:end]
            notes.append(Note(
                _keyword(words[0][0]),
                fix_digits(" ".join(t[0] for t in words)),
                (min(t[1] for t in words), min(t[2] for t in words), max(t[3] for t in words), max(t[4] for t in words)),
            ))
    return notes
