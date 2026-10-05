---
extension: ".COT"
name: 舊版重測資料處理系統二進位檔
category: 舊版二進位檔
location: 重測段目錄
file_pattern: "$$####.COT"
data_type: 二進位（格式未公開）
format_spec: none
sources:
  - 簡介.md §103、重測系統使用手冊Win1.md §203（檔案附加名定義）
  - 重測系統使用手冊Win1.md §409「協助指界檔（CONSTOUT）」
---

# .COT 舊版重測系統二進位檔

## 用途

舊版重測資料處理系統之二進位檔（與 .PUN/.BUN 並列），依名稱推測為坐標類資料（未經手冊證實）。

## 已知行為

- 「報表、輸出／協助指界檔」功能輸出 `.PUN/.BUN/.COT`，並詢問「請輸入產生 .COT 的點號上限<5000>=」。

## 內容格式

手冊未記載內部格式；外部程式不應直接讀寫。
