"""Image loading."""
from __future__ import annotations

import cv2
import numpy as np


def load_image(data: bytes) -> np.ndarray:
    """Decode image bytes to BGR (works for non-ASCII paths read via np.fromfile)."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("無法讀取圖片")
    return img
