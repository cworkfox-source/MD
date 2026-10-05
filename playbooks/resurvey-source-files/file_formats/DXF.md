---
extension: ".DXF"
name: DXF 文字檔輸出
category: 圖形輸出檔
location: 重測段目錄
file_pattern: "*.DXF（手冊未載明確切檔名）"
data_type: DXF（AutoCAD Drawing Exchange Format，ASCII）
format_spec: partial
sources:
  - 重測系統使用手冊Win1.md §411「產生DXF檔」
---

# .DXF 檔輸出

## 用途

「資料整理／產生DXF檔」將系統資料輸出為 DXF 文字檔，供 CAD 軟體使用。

## 已知行為

- 執行時跳出「輸出項目」對話框，可勾選欲輸出之資料項目。

## 內容格式

DXF 為 AutoCAD 公開之標準交換格式（本系統輸出之圖層/實體對應手冊未載）；解析請依 DXF 標準規格。
