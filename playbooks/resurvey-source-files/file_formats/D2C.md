---
extension: ".D2C"
name: 舊地籍圖界址坐標檔
category: 重測段資料檔（舊地籍圖資料層）
location: 重測段目錄（$$####\）
file_pattern: "$$####.D2C"
data_type: dBASE III 資料庫檔案 (.dbf)
format_spec: full
sources:
  - 簡介.md §103、重測系統使用手冊Win1.md §203（檔案附加名定義）
  - 重測系統使用手冊Win1.md §412「讀取舊地籍圖資料（RO2N）」
  - BA0002.D2C 實際資料庫結構分析
---

# .D2C 舊地籍圖界址坐標檔

## 用途

數化舊地籍圖之界址（舊圖點）坐標資料層。

## 已知行為

- 由「舊地籍圖資料／讀取」自 [.CNT](CNT.md) 讀入。
- 「其他工具／引用舊圖點」可將舊圖點坐標另存為現況點。
- 「讀取舊地籍圖」時宗地資料之「數化面積」欄自動置入。

## 內容格式（依實際檔案分析）

本檔案為標準 **dBASE III 資料庫檔案 (.dbf)**。

### 欄位定義表（Schema）

本資料庫共包含 **10 個欄位**，單條記錄長度為 **60 位元組**。欄位結構如下：

| 欄位序號 | 欄位名稱 | 欄位型態 | 欄位長度 | 小數位數 | 說明 |
| --- | --- | --- | --- | --- | --- |
| 1 | `COT_NUMBER` | N (Numeric) | 5 | 0 | 舊界址點號 |
| 2 | `COT_REF` | N (Numeric) | 2 | 0 | 舊參考點編號 |
| 3 | `COT_Y` | N (Numeric) | 16 | 8 | 舊 Y 坐標 |
| 4 | `COT_X` | N (Numeric) | 15 | 8 | 舊 X 坐標 |
| 5 | `COT_MATTER` | N (Numeric) | 1 | 0 | 界標種類代碼 |
| 6 | `COT_SOURCE` | N (Numeric) | 1 | 0 | 點位來源代碼 |
| 7 | `COT_SURVEY` | N (Numeric) | 2 | 0 | 測量方法 |
| 8 | `COT_MSE` | N (Numeric) | 2 | 0 | 點位中誤差 (MSE) |
| 9 | `COT_REMARK` | C (Character) | 12 | 0 | 點位備註 |
| 10 | `TAU_ID` | N (Numeric) | 3 | 0 | 圖幅號 |
