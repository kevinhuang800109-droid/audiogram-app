"""A Streamlit component: click the box, press Ctrl+V, get the screenshot as image bytes."""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component("paste_box", path=str(Path(__file__).parent))


def decode_data_url(value) -> bytes | None:
    """Bytes of the image in a {"data": "data:image/png;base64,..."} value, or None if it isn't one."""
    try:
        header, payload = value["data"].split(",", 1)
        if not header.startswith("data:image/"):
            return None
        return base64.b64decode(payload, validate=True)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def paste_image(key: str) -> bytes | None:
    """Render the paste box; returns the most recently pasted image's bytes (None until something is pasted)."""
    return decode_data_url(_component(key=key, default=None))
