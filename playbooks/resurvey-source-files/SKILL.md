---
name: resurvey-source-files
description: 讀取／解析「地籍圖重測資料處理系統（視窗版）」的重測原始檔並重建宗地圖形與面積。涵蓋段目錄 .D10~.D2D／.D25／.NTX（dBASE III 與自訂二進位）、重測輸入交換檔 .PTM/.BNI/.CNT/.INN、複丈系統交換檔 .PAR/.BNP/.COA/.RCO、測量輸入檔 .MAC/.CTL。當任務提到重測原始檔、段目錄資料檔、界址點／界址坐標／地號界址、宗地環或面積重建、圖根點坐標、光線法批次計算檔，或直接出現上述任一副檔名（含小寫）時使用。Use when reading Taiwan cadastral resurvey source files (D13/D14 dbf, CNT/BNI/PTM, COA/BNP/PAR, MAC/CTL), rebuilding parcel polygons, or verifying parcel areas.
---

# 讀取重測原始檔

「地籍圖重測資料處理系統（視窗版）」的原始資料分四類。這個 skill 給的是**怎麼讀**：
選檔順序、接續規則、陷阱、以及驗證讀得對不對的方法。
欄位表的**權威來源**一律是 `file_formats/<副檔名>.md`；有出入時以那裡為準，不要用本文覆蓋它。

## 開場三條鐵則

1. **只讀不寫。** 原始檔（Dxx／NTX／MTX／交換檔）在任何讀取任務中都不得修改。
   來源專案（nec_rebuild）唯一合法的寫入層是 `rebuild/src/nec_rebuild/dxx_write.py`（ADR-023），與讀取無關。
2. **坐標是 Y（縱）在前、X（橫）在後**，全系統一致。讀進來立刻轉成 `(X, Y)` 再往下傳，
   否則圖形會整個轉置。TWD97 特徵：X 約 150,000–350,000、Y 約 2,550,000–2,800,000。
3. **編碼是 CP950（Big5）**，不是 UTF-8。用 UTF-8 讀中文註記欄會亂碼或丟例外。

## 分流：看到什麼檔，讀哪一份

| 手上的檔 | 是什麼 | 詳細讀法 |
| --- | --- | --- |
| `.D10`~`.D2D`（`.D23`／`.D25` 除外） | 段目錄資料檔，**dBASE III (.dbf)** | [references/dxx_section_files.md](references/dxx_section_files.md) |
| `.D23` | 區段界，ASCII 文字（空白／逗號／TAB 分隔） | 同上 |
| `.D25` | 測量資料記錄，**非 dBASE**，79 byte 固定二進位 | 同上 |
| `.NTX` / `.MTX` | 索引檔（1024 byte page B-tree），**可刪除、可重建** | 同上（讀取前先問「真的需要嗎」） |
| `.Bxx`（`.B11`、`.B2C`…） | 對應 `.Dxx` 的**備份副本**，格式相同 | 同上 |
| `.PTM` `.BNI` `.CNT` `.INN` | 重測輸入交換檔（固定欄寬文字） | [references/exchange_resurvey.md](references/exchange_resurvey.md) |
| `.PAR` `.BNP` `.COA` `.RCO` | 複丈系統交換檔（ⅠⅡ版／整合版兩種版面） | [references/exchange_cadastral.md](references/exchange_cadastral.md) |
| `.MAC` `.CTL`（`.CEN` `.CT2` `.RAW` `.LIN`） | 測量觀測／控制點輸入檔 | [references/survey_input.md](references/survey_input.md) |
| `.A10` `.B10`~`.B90` `.L1x` `.ERR` `.LOC` | 報表輸出，不是資料來源 | `file_formats/` 對應檔 |

**要幾何就要兩個檔**：點號序列（`.D13`／`.BNI`／`.BNP`）＋ 坐標（`.D14`／`.CNT`／`.COA`）。
屬性檔（`.D11`／`.PTM`／`.PAR`）**完全不含坐標**，單獨拿不出圖形。

**優先序**：目錄裡有 `.D13`＋`.D14` 就用它（段內現況，最權威）；沒有才退回交換檔，
且 `.CNT`＋`.BNI` 優先於 `.COA`＋`.BNP`（`.CNT` 保有參考號，是嚴格更豐富的點來源）。

## 讀錯就整批失真的五個陷阱

1. **跨錄接續**。一筆宗地界址點超過容量就續錄：`.D13` 每錄 8 點、**無序號欄**，
   依檔案物理順序接續到某錄以 `COORD_n = 0` 補零為止；`.BNI`／`.BNP` 每錄 11 點，
   **依「序號」欄由小到大**接續。只讀第一錄＝宗地被腰斬。
2. **圓弧記號在下一組欄位**。`.BNP`／`.BNI` 實體樣本的圓弧是點號的**後綴** `+`／`-`
   （手冊寫成前置的「圓弧碼」欄），固定欄寬切下來剛好落在下一組的 A1 欄。
   用空白切詞會讓 `2094+` 整個 token 解析失敗而丟掉那個角點。
   `.D13`／`.D2B` 的同一件事是 `MIDARC_n = T`（Logical）。
3. **參考點不是界址點**。`.D14` 的 `COT_REF == 0` 才是確定點；`COT_REF > 0` 是參考點
   （`100.23` ＝點 100 的第 23 個參考點，`.98` 保留給街廓點），重建宗地環時必須排除。
   點位主鍵一律用 `COT_NUMBER`，不要用「點號小就是確定點」猜。
4. **兩個地號空間不能混**。舊圖宗地環（`.D2B`／`.BNI`）用**原地號**編 key；
   複丈**整合版** `.BNP` 用**新地號**。BA0338 實測原 13-1 對新 238-0，取錯就完全接不起來。
   `.PAR` 兩組地號都有：`[0:4]/[4:8]` 是原、`[22:26]/[26:30]` 是新。
5. **面積單位不同**。`.D11`／`.PTM`／複丈ⅠⅡ版 `.PAR` 是**公頃**（×10000 得 m²）；
   複丈**整合版** `.PAR` 是**平方公尺**。差 10000 倍的 bug 從這裡來。

## 重建宗地環的標準流程

```
1. 讀坐標 → {點號: (X, Y)}，只收確定點（D14 COT_REF==0）
2. 讀點號序列 → {(段號, 母號, 子號): [點號…]}，含每點的弧中點旗標，續錄先接好
3. 查表換坐標；連續重複點只留一個；首尾同點就去掉尾點（輸出時自動閉合）
4. 點數 < 3、或任一點號查不到坐標 → 不產生 polygon（不要硬湊）
5. 面積：shoelace；弧中點以相鄰三點的解析式真弧取代兩段弦（ADR-075）
6. 地中地（.D12）：父地淨面積 = 外環面積 − 各直屬地中地外環面積
7. 驗證：與 .D11 AREA_NEW（公頃 ×10000）比對，差 ≤ 2 m² 才算可信
```

## 直接用腳本

`scripts/read_resurvey.py` 是純標準函式庫、**唯讀**的實作，可直接跑，也可以整個複製走當範本。

```bash
python playbooks/resurvey-source-files/scripts/read_resurvey.py BA0002
python playbooks/resurvey-source-files/scripts/read_resurvey.py BA0002 --verify-areas
python playbooks/resurvey-source-files/scripts/read_resurvey.py BA0002 --parcel 760-73-9
python playbooks/resurvey-source-files/scripts/read_resurvey.py BA0002 --point 6857
python playbooks/resurvey-source-files/scripts/read_resurvey.py BA0762 --verify-exchange
python playbooks/resurvey-source-files/scripts/read_resurvey.py BA0002/BA0002.D14 --dump
```

可匯入的函式：`read_dbf` / `read_d25` / `parse_cnt` / `parse_coa` / `parse_bni` / `parse_bnp`
/ `parse_ptm` / `parse_par` / `parse_inn` / `parse_rco` / `parse_ctl` / `parse_mac`
/ `read_d13_sequences` / `read_d14_points` / `build_rings` / `polygon_area` / `net_area`。

## 驗收：讀對了才算讀完

任何一支新的讀取程式，交付前至少要能給出這三個數字：

| 檢查 | 怎麼算 | 本 repo 樣本的實測結果 |
| --- | --- | --- |
| dBASE 檔長 | `檔頭長度 + 筆數 × 每筆長度` ＝ 檔案大小（可多 1 byte 的 `0x1A`） | BA0002 全部 22 個 dbf 通過 |
| 宗地成環率 | 成環數 ÷ 宗地數 | BA0002 `.D13` 1,219 宗地成環 1,217（2 筆缺點號坐標） |
| 面積符合率 | 重建面積 vs 登記面積，差 ≤ 2 m² | BA0002 D13+D14 對 D11 **1,209/1,209（100%）**；<br>BA0762 COA+BNP 對 PAR 714/714；DD2138 1,359/1,359 |

面積差 10000 倍→單位搞錯；差一整塊→漏了地中地或吃掉了續錄；
只有含弧宗地不合→圓弧記號讀錯（BA0762 修正前 91.9%、修正後 99.0%）。

`.CNT`／`.COA` **同時是原版匯出「現況成果」的格式**，內容是舊圖還是現況取決於當初由哪個功能產生。
本 repo 的 `.CNT`／`.COA` 樣本逐點等於該段自己的 `.D14`。因此 `.CNT` 環對不上 `.PTM` 的
**原登記**面積是正常的（BA0338 實測只有 69% 相符），不要當成解析錯誤去「修」。

## 權威來源

- 欄位表與逐位元組實測：`file_formats/`（索引見該資料夾 `README.md`）
- 代碼表（調查情形／公私有／使用情形／經界物…）：`file_formats/_codes.md`

下面兩條指向**來源專案 nec_rebuild** 的路徑，不在本 playbook 資料夾內；在其他 repo 使用時忽略即可。

- 來源專案實際讀檔路徑：`rebuild/src/nec_rebuild/legacy_import.py`、`legacy_area.py`、
  `dataset.py`、`arc_geometry.py`；觸發條件見 `docs/legacy_import_file_map.md`
- 已鎖定的設計決策：來源專案 `docs/decision_log.md`（ADR-023／040／041／043／045／046／075／093）
