---
extension: ".CT2"
name: 私有補點輸出檔
category: 控制測量輸入/輸出檔
location: 重測段目錄
file_pattern: "$$????.CT2"
data_type: 文字檔（格式未載明）
format_spec: none
sources:
  - 簡介.md §103、重測系統使用手冊Win1.md §203（其他檔案）
  - 重測系統使用手冊Win1.md §412「產生控制測量輸入檔（CRN2C）」
  - 重測系統使用手冊Win1.md §409「協助指界檔（CONSTOUT）」
---

# .CT2 私有補點輸出檔

## 用途

私有補點（點名 Q 開頭，見 [D20.md](D20.md)）之輸出檔。

## 已知行為

- 「資料輸出、入／控制測量輸入檔／產生（重測版/複丈版）」與 .CTL/.CEN 一併產生。
- 「報表、輸出／協助指界檔」亦輸出 `xxxx.CT2`。
- 「控制測量輸入檔／讀取」功能之說明僅提及讀取 .CTL、.CEN（.CT2 為輸出用）。

## 內容格式

手冊未記載欄位格式。
