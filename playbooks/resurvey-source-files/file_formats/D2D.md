---
extension: ".D2D"
name: 舊地籍圖經界線檔
category: 重測段資料檔（舊地籍圖資料層）
location: 重測段目錄（$$####\）
file_pattern: "$$####.D2D"
data_type: dBASE III 資料庫檔案 (.dbf)
format_spec: full
sources:
  - 簡介.md §103、重測系統使用手冊Win1.md §203（檔案附加名定義）
  - 重測系統使用手冊Win1.md §412「讀取舊地籍圖資料（RO2N）」
  - BA0002.D2D 實際資料庫結構分析
---

# .D2D 舊地籍圖經界線檔

## 用途

數化舊地籍圖之經界線資料層（顯示項設定之「舊地籍圖經界線層」）。

## 已知行為

- 由「舊地籍圖資料／讀取」讀入；三參數轉換套圖時可作點對線之對應條件。

## 內容格式（依實際檔案分析）

本檔案為標準 **dBASE III 資料庫檔案 (.dbf)**。

### 欄位定義表（Schema）

本資料庫共包含 **14 個欄位**，單條記錄長度為 **97 位元組**。欄位結構如下：

| 欄位序號 | 欄位名稱 | 欄位型態 | 欄位長度 | 小數位數 | 說明 |
| --- | --- | --- | --- | --- | --- |
| 1 | `LIN_TOP` | N (Numeric) | 5 | 0 | 起點點號 |
| 2 | `LIN_MID` | N (Numeric) | 5 | 0 | 弧形邊界之中間點號（若非弧形，此欄為 0） |
| 3 | `LIN_BOT` | N (Numeric) | 5 | 0 | 終點點號 |
| 4 | `L_SECTION` | N (Numeric) | 4 | 0 | 左側舊段號 |
| 5 | `L_PARCEL` | N (Numeric) | 4 | 0 | 左側舊地號母號 |
| 6 | `L_PARCEL_E` | N (Numeric) | 4 | 0 | 左側舊地號子號 |
| 7 | `R_SECTION` | N (Numeric) | 4 | 0 | 右側舊段號 |
| 8 | `R_PARCEL` | N (Numeric) | 4 | 0 | 右側舊地號母號 |
| 9 | `R_PARCEL_E` | N (Numeric) | 4 | 0 | 右側舊地號子號 |
| 10 | `LIN_MODE` | N (Numeric) | 1 | 0 | 經界線連線模式/種類 |
| 11 | `R_EXAM` | C (Character) | 20 | 0 | 右側審查註記 |
| 12 | `L_EXAM` | C (Character) | 20 | 0 | 左側審查註記 |
| 13 | `R_IDENT` | C (Character) | 8 | 0 | 右側識別碼 |
| 14 | `L_IDENT` | C (Character) | 8 | 0 | 左側識別碼 |
