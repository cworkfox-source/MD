---
extension: ".LIN"
name: 外業自動化連線資料檔
category: 測量觀測輸入檔
location: 任意目錄
file_pattern: "*.LIN"
data_type: 固定寬度文字檔（ASCII，CRLF）
format_spec: full
sources:
  - 重測系統使用手冊Win1.md §412「讀取 .LIN（RLIN）」
  - lin-test/test.lin 實際樣本（11,862 筆）byte-for-byte 分析
---

# .LIN 外業自動化連線資料檔

## 用途

外業自動化之**連線（線段）資料檔**，經「資料輸出、入／讀取 .LIN（RLIN）」讀入系統。
內容為**點對點連線拓樸**：每筆一條連線，只記兩個端點點名。

## 內容格式（依實際樣本分析，byte-for-byte 驗證）

純 ASCII 固定寬度文字檔，**無檔頭、無檔尾**。每筆記錄長度固定 **19 bytes ＋ `CRLF`**，
共兩個欄位，皆為**左靠、空白補齊**的點名：

| 欄位 | 位元組位置 | 寬度 | 型別 | 說明 |
| --- | --- | --- | --- | --- |
| 1 | 0–9 | 10 | ASCII 字串（左靠補空白） | 起點點名 |
| 2 | 10–18 | 9 | ASCII 字串（左靠補空白） | 終點點名 |

樣本 `lin-test/test.lin`：11,862 筆 × 21 bytes（19 ＋ CRLF）＝ 249,102 bytes，與檔案大小完全吻合。
原版全確定點樣本等同 `%-10d%-9d`；重建版點名格式為 `%-10s%-9s`，全為確定點時
byte-for-byte 相同。確定點寫 `n`，參考點寫 `n.r`（參考號不補零）。

### 已知語意

- 只記**連線拓樸**：無弧中點、無參考線層、無左右宗地、無座標（與 [D21](D21.md)/[D29](D29.md) 不同）。
- 為**無方向圖**：同一點可出現在多筆記錄（如點 1 同時連 2、3129、3130），且欄位順序不固定（有時大號在前）。
- 實測 `test.lin` 的 D21 來源全為整數確定點；重建版另支援 D29 的 `母.子` 文字點名。
- `test.D21` 有 11,877 筆，其中 15 筆 `LIN_MID != 0`；移除圓弧後的 11,862 筆
  `(LIN_TOP, LIN_BOT)` 與 `test.lin` 逐筆、方向、重複數完全相同，證實原版輸出會捨棄圓弧。

## 重建版來源與圓弧擴充

- 預設來源為 D29 參考線；亦可選 D21 經界線或兩者，並可依 D29 `LIN_MODE` 0–9 篩選。
- 直線寫入 `<name>.LIN`。
- 圓弧預設分離至自訂 `<name>-ARC.LIN`，格式 `%-10s%-10s%-9s`，三欄依序為起點、
  弧中點、終點；此格式不是原版反解結果，原版不能假設可讀。
- D29 端點若為 `C326C069` 等控制點名，由匯出政策決定略過、連坐標一併輸出或中止。
- D29 必須直接讀 `EditWorkspace.reference_lines`，不可改用 `SectionView.reference_lines`：
  後者不保留 `LIN_MID`，且會跳過非數值控制點端點。

## 匯出實作

重建版 [`nec_rebuild/lin_export.py`](../../rebuild/src/nec_rebuild/lin_export.py) 提供
`write_lin` / `parse_lin` 與來源、層別、框選、控制點、圓弧分離資料準備。回歸測試以
`test.lin` 做 byte-for-byte 驗證；`-ARC.LIN` 的檔首註解與三點格式由重建版規格釘住。
