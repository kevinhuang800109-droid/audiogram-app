import base64
from pathlib import Path

from paste_box import decode_data_url


def test_decodes_png_data_url():
    raw = b"\x89PNG\r\n\x1a\nfake"
    url = "data:image/png;base64," + base64.b64encode(raw).decode()
    assert decode_data_url({"data": url, "ts": 1}) == raw


def test_rejects_non_images_and_garbage():
    assert decode_data_url(None) is None
    assert decode_data_url({}) is None
    assert decode_data_url({"data": "data:text/plain;base64,aGk="}) is None
    assert decode_data_url({"data": "data:image/png;base64,@@@"}) is None
    assert decode_data_url({"data": "no-comma"}) is None


def test_frontend_is_shipped_next_to_the_package():
    html = (Path(__file__).resolve().parents[1] / "paste_box" / "index.html").read_text(encoding="utf-8")
    assert "streamlit:setComponentValue" in html and "paste" in html
