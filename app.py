"""Streamlit front end: upload an audiogram, check the detections, edit, read the 4-frequency averages."""
import hashlib

import cv2
import pandas as pd
import streamlit as st

from audiogram.calc import AVG_FREQS, FREQS, four_freq_average
from audiogram.pipeline import analyze
from audiogram.report import build_report, round_half_up
from paste_box import paste_image

LABELS = {
    ("right", "AC"): "右耳 氣導 (O)",
    ("left", "AC"): "左耳 氣導 (X)",
    ("right", "BC"): "右耳 骨導 (<)",
    ("left", "BC"): "左耳 骨導 (>)",
}

st.set_page_config(page_title="聽力圖分析", layout="wide")
st.title("純音聽力圖分析")
st.caption("貼上或上傳聽力圖 → 自動讀出各頻率聽閾 → 可手動修正 → 計算 500/1000/2000/4000 Hz 四頻平均")

st.warning("此為公開網站：請勿上傳含可辨識病患姓名、病歷號等個人資料的圖片。")
mode = st.radio("圖片來源", ["貼上截圖", "上傳檔案"], horizontal=True, label_visibility="collapsed")
if mode == "貼上截圖":
    data = paste_image(key="paste")
    if data is None:
        st.info("用 Win+Shift+S（或 Print Screen）截下聽力圖，點一下上方的框，再按 Ctrl+V。")
else:
    upload = st.file_uploader("聽力圖圖片", type=["png", "jpg", "jpeg", "bmp"])
    data = upload.getvalue() if upload is not None else None
if data is None:
    st.stop()
image_id = hashlib.md5(data).hexdigest()[:8]  # new image -> new widget keys, so the text boxes reset

try:
    result = analyze(data)
except Exception as exc:  # grid/axis detection can fail on unusual layouts
    st.error(f"無法分析此圖片：{exc}")
    st.stop()

left, right = st.columns([3, 2])
with left:
    st.subheader("偵測結果疊圖")
    st.image(cv2.cvtColor(result.overlay, cv2.COLOR_BGR2RGB), width="stretch")
    st.caption("綠線 = 偵測到的格線，橘圈 = 偵測到的符號，數字 = 讀出的 dB HL")
    for note in result.axes.notes:
        st.warning(note)

with right:
    st.subheader("各頻率聽閾 (dB HL)")
    st.caption("空白 = 未偵測到。可直接修改儲存格，平均值會即時更新。")
    table = pd.DataFrame(
        {f"{f} Hz": [result.thresholds[key][f] for key in LABELS] for f in FREQS},
        index=list(LABELS.values()),
        dtype="float",
    )
    edited = st.data_editor(table, width="stretch")

    st.subheader("四頻平均 (500/1000/2000/4000 Hz)")
    cols = st.columns(2)
    for i, (key, label) in enumerate(LABELS.items()):
        row = edited.loc[label]
        th = {f: (None if pd.isna(row[f"{f} Hz"]) else float(row[f"{f} Hz"])) for f in FREQS}
        avg = four_freq_average(th)
        missing = [f for f in AVG_FREQS if th[f] is None]
        with cols[i % 2]:
            if avg is None:
                st.metric(label, "—", help=f"缺少 {', '.join(map(str, missing))} Hz")
            else:
                st.metric(label, f"{round_half_up(avg)} dB")

    st.download_button("下載 CSV", edited.to_csv().encode("utf-8-sig"), "audiogram.csv", "text/csv")

st.divider()
st.subheader("Comments（以下全部文字）")
st.caption("「Comments」以下的所有文字與數字，可直接修改後複製。OCR 可能讀錯，請對照右側原圖。")
comments_text = ""
if result.comments is None:
    st.info("圖中未找到 Comments。")
else:
    text_col, crop_col = st.columns([3, 2])
    with text_col:
        comments_text = st.text_area("Comments", result.comments.text, height=220, key=f"comments-{image_id}", label_visibility="collapsed")
    with crop_col:
        st.image(cv2.cvtColor(result.comments.crop(result.image), cv2.COLOR_BGR2RGB), width="content")

st.divider()
st.subheader("附註文字 (Tympanogram / SRT / SRS)")
st.caption("照抄圖中文字，不做分析。OCR 可能讀錯，請對照右側原圖裁切後直接修改。")
if not result.notes:
    st.info("圖中未找到 Tymp / SRT / SRS 文字。")
note_texts = []
for i, note in enumerate(result.notes):
    text_col, crop_col = st.columns([3, 2])
    with text_col:
        note_texts.append(st.text_input(note.kind, note.text, key=f"note-{image_id}-{i}"))
    with crop_col:
        st.image(cv2.cvtColor(note.crop(result.image), cv2.COLOR_BGR2RGB), width="content")

st.divider()
st.subheader("報告文字（可直接複製）")
st.caption("由上方修改後的聽閾、Tymp/SRT/SRS 與 Comments 整理而成；缺值不會顯示。可在框內再編輯，Ctrl+A 全選後複製。")
edited_thresholds = {
    key: {f: (None if pd.isna(edited.loc[label, f"{f} Hz"]) else float(edited.loc[label, f"{f} Hz"])) for f in FREQS}
    for key, label in LABELS.items()
}
report = build_report(edited_thresholds, note_texts, comments_text)
# keyed on the text itself so the box refreshes whenever a value above is corrected
st.text_area("報告", report, height=300, key=f"report-{hash(report)}", label_visibility="collapsed")
