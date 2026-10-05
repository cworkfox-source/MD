# Playbook: Embeddable Python Packaging（取代 Nuitka/PyInstaller 打包）

> 適用於任何 AI coding agent（Claude Code、Google Antigravity、Codex、Cursor、...）。
> 這份文件不依賴任何特定工具的 skill/plugin 機制，純 Markdown，讀了就能照著做。

## 何時該查這份文件

當任務是「把 Python 腳本打包成給不懂技術的使用者雙擊執行的形式」，且滿足下列
任一情況時，先讀這份文件再動手：

- 使用者提到 Nuitka、PyInstaller、cx_Freeze，或正在用這類工具打包
- 使用者說打包後的 exe 被防毒軟體（趨勢科技、Windows Defender 等）誤判為病毒、
  攔截、隔離、刪除
- 使用者想要「不用裝 Python 也能執行」的可攜式發佈方式
- 使用者擔心程式碼簽章成本，或單純想先試試免費的替代方案

## 這個方法解決什麼問題

Nuitka `--onefile`、PyInstaller `--onefile` 會把整個 Python 直譯器 + 程式壓縮進
**單一 exe**，執行時自我解壓到暫存目錄再跑。這個「自解壓單檔」模式，剛好和很多
惡意軟體的手法一樣（高熵壓縮段、無數位簽章、單檔案、執行期展開），所以防毒軟體
（尤其企業級 AV 的啟發式/行為偵測）很容易誤判，即使程式碼本身完全乾淨也一樣。

**核心解法**：不編譯成單一 exe，改用 [Python 官方 Embeddable Package]
(https://www.python.org/downloads/windows/，頁面上找 "Windows embeddable package")——
一個由 PSF（Python Software Foundation）數位簽章過的精簡版 `python.exe`，搭配純
文字的 `.py` 原始碼一起發佈。少了「自解壓單檔」這個最大的誤判特徵，靜態掃描的
信任分數會明顯提升。

這**不是**保證 100% 不被攔截（行為監控仍可能因為程式的實際動作，例如自動化點擊
瀏覽器，觸發警示），但能排除一大類最常見的誤判來源，而且完全免費、不需要買程式
碼簽章憑證。

## 何時適合用這個方法（先做這一步判斷）

這個方法對「依賴單純」的專案效果最好、阻力最小。開始動手前，先確認：

1. **列出專案唯一或所有第三方套件**，到目標的 venv/site-packages 找有沒有
   `.pyd`（Windows）或 `.so`（其他平台）檔案。有 `.pyd` 不代表不能用這個方法，
   但代表那個套件需要「該套件在 PyPI 上有沒有對應 Python 版本 + Windows 平台的
   預編譯 wheel」——如果有現成 wheel（多數主流套件都有，例如 `cffi`、
   `cryptography`、`numpy`、`pandas`），pip 安裝時會直接下載 wheel，不需要在
   目標機器上編譯任何東西，這個方法完全適用。
   詳細判斷準則見 `references/compatibility-check.md`。

2. **確認程式有沒有用到 GUI framework**。純 console/CLI 腳本最簡單。
   如果用 tkinter，注意嵌入版預設**沒有**打包 tcl/tk，需要額外處理
   （見 `references/troubleshooting.md`）。PyQt/PySide 通常可行但體積會大很多。

3. **確認程式執行期需不需要連網下載其他東西**（例如 Selenium 的
   selenium-manager 會自動抓 chromedriver）。如果需要，目標機器發佈時
   要保留這個網路需求的說明，或考慮改成離線指定路徑。

如果專案有非純 Python 且沒有對應 wheel 的 C 擴充套件，這個方法會卡住（無法在
嵌入版環境編譯），這時候老實跟使用者說明，另外考慮數位簽章 Nuitka exe，或評估
能不能換掉那個依賴。

## 標準作業流程（SOP）

### 步驟 0：建立獨立的發佈用資料夾

不要直接在原本的開發專案（有 venv 的那個）裡面改。建立一個新的、獨立的資料夾，
做出清楚區隔，結構如下（如果使用者已有現成專案要打包，直接在旁邊建一個新資料夾，
例如 `原專案名_embed/`）：

```
專案名_embed/
├── python_embed/       # 官方 Embeddable Package 解壓後的內容
├── src/
│   └── 主程式.py         # 從原專案複製過來的原始碼
├── requirements-embed.txt  # 由乾淨 venv 凍結出的依賴鎖定清單（見步驟 3）
├── start.bat            # 使用者雙擊執行的進入點（內容見下方，檔名可用中文）
├── README.md
└── docs/                 # 如果專案有文件治理規範（例如 AGENTS.md），比照辦理
```

### 步驟 1：下載並解壓 Embeddable Package

先確認開發環境用的 Python **major.minor** 版本（例如 3.11），到
`https://www.python.org/ftp/python/<version>/python-<version>-embed-amd64.zip`
下載對應版本。**不需要跟開發環境的 patch version 完全一致**——`.pyd` 檔的
ABI tag 只綁定 major.minor（例如都是 `cp311`），patch version 不影響相容性。
如果不確定有沒有更新的 3.11.x 版本，直接查 python.org 的下載頁確認最新
patch release。

解壓縮到 `python_embed/`。

### 步驟 2：啟用 site 模組（關鍵，不做這步 pip 裝的套件全部讀不到）

打開 `python_embed/python<XXX>._pth`（XXX 是版本數字，例如 3.11 就是
`python311._pth`），內容預設類似：

```
python311.zip
.

# Uncomment to run site.main() automatically
#import site
```

改成：

```
python311.zip
.
Lib\site-packages

# Uncomment to run site.main() automatically
import site
```

也就是：拿掉 `#import site` 前面的 `#`，並加入 `Lib\site-packages` 這一行。
少了這步，之後 pip 裝的套件會完全 import 不到（`ModuleNotFoundError`），
即使裝的時候看起來成功。

### 步驟 3：用乾淨 venv 鎖定依賴清單，再安裝進嵌入版環境

**依賴清單一律從一個乾淨的 venv 產生，絕對不要直接照抄開發環境或全域環境的
site-packages / `pip freeze`**。開發用的 venv 常會累積實驗過但實際沒用到的
套件，全域環境更是；直接照抄會把不必要的元件一起打包進去，體積膨脹、誤判
風險面也跟著變大。正確做法：

3-1. 在原專案旁建立一個臨時的乾淨 venv（打包完成後即可整個刪除）：

```
python -m venv venv_pack
```

3-2. 只安裝「主程式原始碼實際 import 到」的**直接依賴**——掃過所有要發佈的
`.py` 檔裡的 import 語句來推導清單；不要看到舊的 `requirements.txt` 就照單
全收（裡面可能有已經不用的東西），推導結果不確定時問使用者：

```
venv_pack\Scripts\python.exe -m pip install <直接依賴1> <直接依賴2> ...
```

3-3. 凍結出鎖定清單（pip 解析出來的必要子依賴與確切版本會自動包含在內）：

```
venv_pack\Scripts\python.exe -m pip freeze > requirements-embed.txt
```

3-4. 嵌入版環境安裝 pip 後，一律用這份清單安裝，不要再手動逐一 pip install：

```
curl -sL -o python_embed/get-pip.py https://bootstrap.pypa.io/get-pip.py
python_embed/python.exe python_embed/get-pip.py --no-warn-script-location
python_embed/python.exe -m pip install -r requirements-embed.txt
```

（Windows 環境可用 PowerShell 的 `Invoke-WebRequest` 代替 `curl -o`。）

這樣 `python_embed/Lib/site-packages` 裡就是必要元件的最小集合：體積可控、
版本可重現，`requirements-embed.txt` 留在發佈資料夾裡也方便日後重建或稽核。
步驟 1 檢查 Python 版本、以及 `references/compatibility-check.md` 的 `.pyd`
掃描，都改成對 `venv_pack` 做，結果才反映實際要打包的內容。

裝完之後用 `python_embed/python.exe -c "import <套件>; print('OK')"` 驗證每個
專案實際會用到的 import 都能成功——不要只驗證主套件，把原程式開頭所有 `import`
語句都測一遍，因為子依賴裝漏或版本不合的情況不少見。

### 步驟 4：複製 VC++ Runtime DLL（低成本保險）

從系統複製兩個檔案到 `python_embed/`（和 `python.exe` 同一層）：

```
C:\Windows\System32\vcruntime140.dll
C:\Windows\System32\vcruntime140_1.dll
```

多數 Windows 已經內建這些，但少數精簡/乾淨安裝的系統會缺，複製這兩個檔案幾乎
零成本就能排除這個問題。

### 步驟 5：瘦身（可選但建議）

`pip`、`setuptools`、`wheel` 只在安裝套件時需要，執行期程式不會 import 它們，
可以安全刪除縮小體積：

```
rm -rf python_embed/Lib/site-packages/pip python_embed/Lib/site-packages/pip-*.dist-info
rm -rf python_embed/Lib/site-packages/setuptools python_embed/Lib/site-packages/setuptools-*.dist-info
rm -rf python_embed/Lib/site-packages/wheel python_embed/Lib/site-packages/wheel-*.dist-info
rm -f python_embed/Scripts/pip*.exe
find python_embed -type d -name "__pycache__" -exec rm -rf {} +
```

刪除後**重新跑一次步驟 3 的 import 驗證**，確認沒有誤刪執行期需要的東西。

### 步驟 6：複製主程式，並檢查資料檔路徑是否錨定正確

把原程式複製到 `src/`。**檢查程式裡任何讀寫本機資料檔的路徑**（設定檔、進度
紀錄、log），確保是用下面這種方式錨定在腳本自身所在目錄，而不是相對路徑或
依賴目前工作目錄：

```python
import os
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
```

原因：使用者可能從不同位置啟動（捷徑、拖曳、不同工作目錄），純相對路徑
（例如 `DATA_FILE = "data.json"`）在換了啟動方式後會讀不到既有資料，是一個
容易被忽略但很常見的 bug。

### 步驟 7：撰寫 `start.bat`（這步最容易踩雷，務必看完）

直接用 `assets/start.bat.template` 當起點，把 `PYTHON_EXE` 和 `SCRIPT_PATH`
換成實際路徑即可。三個關鍵規則：

1. **用 `python.exe`，絕對不要用 `pythonw.exe`**——如果主程式有任何 `input()`
   呼叫或需要 console 互動，`pythonw.exe` 沒有 console，程式會卡住或直接失敗。
   只有在程式完全是背景執行、不需要使用者看到任何輸出/互動時才考慮
   `pythonw.exe`。

2. **`.bat` 檔內容一律使用純 ASCII（英文），絕對不要放中文字**，也不要加
   `chcp 65001`。這是一個真實發生過、很容易被忽略的地雷：`.bat` 檔如果用
   UTF-8 編碼但系統預設 codepage 是繁中 Big5（多數台灣/繁中 Windows 都是），
   即使加了 `chcp 65001` 也沒用——因為 `chcp 65001` 這行本身要先被舊的 Big5
   codepage 解析過一次才會生效，在切換完成之前，檔案裡的中文 UTF-8 多位元組
   字元會被 Big5 逐位元組誤讀拆解，把後面所有行的路徑變數、指令都讀壞，導致
   整支 `.bat` 完全無法執行，錯誤訊息會是一堆看起來莫名其妙的「XXX 不是內部
   或外部命令」。純 ASCII 內容在任何系統 codepage 下都會被正確解析，不隨語系
   而異，是唯一真正穩妥的解法。（`.bat` 檔的**檔名**可以用中文，例如
   `啟動.bat`，這沒問題——Windows 檔名走 Unicode，和批次檔內容解析是兩回事。）

3. **用 `cd /d "%~dp0"` 把工作目錄固定在批次檔自身所在資料夾**，這樣即使
   主程式的資料檔路徑沒有像步驟 6 那樣完全錨定，至少工作目錄是可預期的。

完整踩坑細節與其他常見錯誤見 `references/troubleshooting.md`。

### 步驟 8：煙霧測試（Smoke Test）

用 `scripts/smoke_test.py` 當模板，改成實際專案用到的 import，跑一次確認沒有
任何 `ImportError`。如果程式會啟動瀏覽器（Selenium 這類），實際跑一次啟動 +
關閉，確認 selenium-manager 等自動下載機制能正常運作。

### 步驟 9：發佈前檢查清單

- [ ] 刪除所有個人資料檔（進度紀錄、設定檔、log），不要把自己的使用紀錄一併
      打包發出去
- [ ] 確認 `start.bat` 是純 ASCII（可用 `file start.bat` 確認顯示 `ASCII text`
      而非 `UTF-8 Unicode text`）
- [ ] 實際在乾淨環境（或至少換一個工作目錄）雙擊執行一次，走過完整流程
- [ ] 整個資料夾壓縮成 zip，這就是交付物；對方解壓後雙擊 `.bat` 即可，不需要
      安裝任何 Python 環境

### 步驟 10：老實告知使用者這個方法的邊界

跟使用者說清楚：這個方法大幅降低「靜態掃描誤判」的機率，但不是 100% 保證。
如果對方電腦的防毒軟體仍然攔截，建議準備一份「如何把資料夾加入防毒軟體白名單/
例外清單」的簡短說明一起附上，這是最實際的最後一道防線。

## 延伸資源

- `references/compatibility-check.md` — 如何判斷一個套件能不能在這個方法下
  正常運作（C 擴充、wheel 可得性、GUI framework 的注意事項）
- `references/troubleshooting.md` — 完整踩坑記錄（`.bat` 編碼問題、tkinter
  缺失、vcruntime 缺失、pip 安裝失敗等）與各自的解法
- `assets/start.bat.template` — 可直接複製修改的啟動腳本模板
- `scripts/smoke_test.py` — 煙霧測試腳本模板

## 這份 Playbook 與 Claude Code Skill 的關係

Claude Code 使用者可以在 `~/.claude/skills/embeddable-python-packaging/SKILL.md`
找到一個會自動觸發的薄包裝版本，內容指回這份文件，避免兩處內容重複維護。
其他工具（Google Antigravity、Codex、Cursor 等）沒有這層自動觸發機制，
所以請直接把這份 `PLAYBOOK.md` 的路徑放進專案的 `AGENTS.md`（見
`@@MD規則/AGENTS.md` 的「Reusable Playbooks」區塊），或在需要時手動指給
agent 讀取此檔。
