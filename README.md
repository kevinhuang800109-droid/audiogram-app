# 聽力圖分析

讀取純音聽力圖圖片，用影像處理 + Tesseract OCR 讀出每個頻率的聽閾（dB HL），並計算
500 / 1000 / 2000 / 4000 Hz 的四頻平均 `(500+1000+2000+4000)/4`。左右耳、氣導(AC)與骨導(BC)皆支援。

## 部署成網址（Streamlit Community Cloud）＋嵌入 Google Sites

Google Sites 本身不能執行 Python，所以程式放在 Streamlit Community Cloud，再嵌入 Sites。

1. 把本資料夾推到 GitHub repo（`packages.txt` 會讓雲端自動安裝 Tesseract；`.gitignore` 已排除真實聽力圖）。
2. 到 https://share.streamlit.io 用 GitHub 登入 → New app → 選 repo、branch、主檔 `app.py`，
   Advanced settings 的 Python 版本選 3.12 → Deploy。
3. 得到 `https://<名稱>.streamlit.app`，這就是可直接分享的網址。
4. Google Sites：編輯頁面 → 插入 → 嵌入 → 透過網址 → 貼上 `https://<名稱>.streamlit.app/?embed=true`，
   區塊高度調到 1200px 以上 → 發布。

公開網站任何人都能上傳圖片，請勿上傳含病患個人資料的圖片。免費方案閒置後會休眠，首次開啟需等幾十秒。

## 在另一台電腦安裝（Windows）

1. 先安裝 Python 3.11 以上（https://www.python.org/downloads/ ，安裝時勾選 Add python.exe to PATH）。
2. 解壓縮 `audiogram-app.zip`，放在**路徑不含中文**的資料夾（例如 `C:\audiogram`）較保險。
3. 點兩下 `setup.bat`：會自動安裝 Tesseract OCR、建立虛擬環境並安裝套件（需要網路，只需做一次）。
4. 之後點兩下 `run.bat` 就會啟動，瀏覽器開啟 http://localhost:8501 。

## 手動安裝

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
winget install UB-Mannheim.TesseractOCR
```

Tesseract 若不在預設路徑 `C:\Program Files\Tesseract-OCR\tesseract.exe`，請設定環境變數 `TESSERACT_CMD`。

## 使用

```
.venv\Scripts\python -m streamlit run app.py
```

上傳圖片後會顯示偵測疊圖與可編輯的結果表；辨識有誤時直接改儲存格，平均值會跟著更新。

## 測試

```
.venv\Scripts\python -m pytest
.venv\Scripts\python tools\make_synthetic.py synthetic.png   # 產生已知答案的合成聽力圖
```

## 附註文字（Tympanogram / SRT / SRS）

圖中若有以 `Tymp` / `Tympanogram`、`SRT`（或同義的 `SDT`，歸為 SRT）、`SRS` 開頭的文字，程式會用 OCR **照抄整串文字**（例如
`Tymp Rt type A Lt type B`），不做任何解讀；介面上可修改，並附原圖裁切方便核對。
同一行有多個關鍵字時會依關鍵字切開；換行延續的文字目前不會併入。
小圖的 OCR 可能讀錯字，以裁切圖為準。目前只用合成文字測試，尚未用真實附註圖驗證。

## 貼上截圖（不用存檔）

Win+Shift+S（或 Print Screen）截下聽力圖 → 在網頁上點一下「貼上框」→ Ctrl+V，立刻分析。
也可把圖片檔拖曳到框內；原本的「上傳檔案」模式仍保留（上方切換）。
貼上框是自訂元件，放在 `paste_box/`（純 HTML/JS，無需額外安裝）。

## 報告文字

頁面最下方會把（修改後的）聽閾、四頻平均、Tymp/SRT/SRS 與 Comments 整理成一段文字，可再編輯、全選複製。
格式：`Rt 45-50-50-40-45-40`、`Lt ...`，六個數字依序是 250 / 500 / 1000 / 2000 / 4000 / 8000 Hz 的氣導，
某頻率沒讀到顯示 `?`；骨導不列在這兩行。接著是 `4-frequency average (...)` 一行（骨導四頻齊全時也會列出）。
平均值四捨五入到小數一位（.5 進位）。

## Comments

圖中若有「Comments」標題，其**以下的所有文字與數字**（PTA、SDT、Tymp… 全部）會整段 OCR 成文字，
放在可編輯的文字框裡方便複製；欄位之間的大空隙會轉成兩個空格。標題同一行後面的文字也會一併納入。
只認英文，OCR 讀錯處請對照右側原圖修正。

## 目前的假設與限制

- 以顏色判斷耳別：紅 = 右耳、藍 = 左耳。氣導：O / X，遮蔽氣導 △ / □（併入氣導）；骨導：`<` `[` / `>` `]`。黑白圖尚未支援。
- 座標軸只靠 OCR 讀刻度文字（125…12K、-10…120 dB）校準，不依賴格線；刻度文字讀不到時會報錯。
- dB 以 5 dB 為單位四捨五入；頻率吸附到最近的標準頻率。
- 750 / 1.5K / 3K / 6K 欄位須有更高信心才會採用（連線經過時容易被誤認成符號）。
- 氣導已用 5 張真實圖調校，圖 1、2、5 有逐值回歸測試；**骨導**較不穩（小、點線、常與氣導重疊），藍色骨導在圖 5 漏判，請檢查表格。
- 尚未處理「無反應」（向下箭頭）符號。
