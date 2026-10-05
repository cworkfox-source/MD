---
extension: ".NTX"
name: 索引檔（可刪除）
category: NECSYS 目錄（測區共用）
location: \NECSYS
file_pattern: "*.NTX"
data_type: 1024-byte page B-tree 類索引檔（讀取、完整 B-tree 重建及 type 4／.MTX 複合索引重建均已確認；原版增量寫入行為未驗證）
format_spec: verified-full-rebuild
sources:
  - 簡介.md §103、重測系統使用手冊Win1.md §203（檔案附加名定義）
  - BA0001／BA0002 之 9 個 NTX 與 2 個 MTX 實檔 header 與資料頁（雙樣本交叉驗證）
  - NECEXE 反編譯 `DBFLIB/Ntxbase1.cpp`、`Ntxbasec.cpp` 殘留與 `FUN_009e2568`／`FUN_009e26bc`／`FUN_009e33d8`
  - Harbour `src/rdd/dbfntx/dbfntx1.c`（外部相容實作，僅作交叉參考）
  - `tools/verify_ntx_structure.py`（可重跑；見 `analysis/symbol_recovery/ntx_structure_verification.json`）
---

# .NTX 索引檔

## 用途

系統與工作段使用的索引檔；手冊註明**可刪除**（系統可重建）。BA0002 實際含 9 個 `.NTX` 與 2 個同族 `.MTX`。

## 內容格式

手冊未記載內部格式。下列結構由 BA0001／BA0002 實檔與反編譯交叉確認；讀取路徑與「整檔重新建立 B-tree」已完成副本回歸。原版逐筆增量更新、free-page reuse 與鎖定規則仍未確認，因此不仿作增量寫入。

## 已確認結構

- 11 個實檔大小均為 **1024 bytes 的整數倍**。
- `FUN_009e33d8` 以 `memcpy(..., 0x400)` 複製索引頁；`Ntxbase1.cpp` / `Ntxbasec.cpp` 路徑殘留在相鄰平衡與節點操作。
- Harbour 的 DBFNTX 相容實作同樣以 `NTXBLOCKSIZE` 讀寫 page；這是外部交叉參考，不代表兩者每個欄位都完全相同。

### 第一頁 header（小端序）

| Offset | 長度 | 目前解讀 | BA0002 驗證 |
|---:|---:|---|---|
| 0 | 2 | signature | 全部為 `6` |
| 2 | 2 | 檔內子索引（order）數 | NTX 為 `1`；MTX 為 `4`，與實際 header 頁數一致（見下方 .MTX 一節） |
| 4 | 4 | root page byte offset | 全部為 1024 的倍數且落在檔案內 |
| 8 | 4 | page 管理欄位 | BA0002 全為 0；精確語意待驗證 |
| 12 | 2 | item size | 與 key size 及 page 容量一致 |
| 14 | 2 | key size | 例如 COORDS.NTX 為 7 |
| 16 | 2 | key decimals | 樣本可讀，語意待更多數值 key 驗證 |
| 18 | 2 | page 最大 key 數 | 例如 COORDS.NTX 為 58 |
| 20 | 2 | half-page key 數 | 與分裂/合併門檻相符，仍待動態驗證 |
| 22 | 最多 256 | NUL 結尾 key expression | 可直接讀出欄位索引運算式 |

完整實檔結果見 `analysis/symbol_recovery/index_headers.csv`。例如：

- `COORDS.NTX`：`STR(COT_NUMBER,5)+STR(COT_REF,2)`
- `LAND_N.NTX`：`STR(SECTION_N,4)+STR(PAR_N_M,4)+STR(PAR_N_C,4)`
- `TMBL.MTX`：`STR(LIN_TOP,5)`

## 資料頁內部排列（type 1／.NTX，已確認）

以反編譯 `Ntxbase1.cpp`/`Ntxbasec.cpp` 候選函式（`FUN_009e2568`/`FUN_009e26bc` 的
key/page stack 搬移、`FUN_009e33d8` 的 0x400-byte page copy＋key 位移）為線索提出假說，
再用 `tools/verify_ntx_structure.py` 對 BA0001／BA0002 的實際索引位元組逐筆解碼、
回頭比對同一筆記錄在對應 `.Dxx` 表裡的真實欄位值——兩個獨立樣本、`COORDS.NTX`
（單欄位 key，7,721＋9,554 筆）與 `LAND_N.NTX`（三欄位複合 key，各 3,506 筆）
共 24,287 筆全數一致，**零筆不符**：

```text
page（1024 bytes）:
  offset 0        : 2-byte 本頁已用項目數（used_count）
  offset 2        : (max_keys + 1) 個 2-byte 頁內偏移量的目錄
                     （即 base_offset = 2 * (max_keys + 2)）
  offset base_offset 起 : used_count 個項目，依目錄位置依序排列

item（item_size bytes，例如 COORDS.NTX 為 15 bytes）:
  offset 0  (4 bytes, little-endian) : child page 的檔案位元組偏移量（無子頁時為 0）
  offset 4  (4 bytes, little-endian) : 對應 .Dxx 表的 1-based 記錄編號
  offset 8  (key_size bytes)         : key 文字（依 STR(...) 右靠齊，ASCII）
```

`item_size - key_size` 在全部 11 個索引都固定是 8（＝4-byte child pointer ＋
4-byte record number），這個差值本身就是全樣本一致的證據。非零的 child pointer
全部是 1024 的倍數且落在檔案範圍內，符合「B-tree 子頁位元組偏移」的預期。

## `.MTX`（header offset 2 = 4）＝複合索引檔（已確認）

`.MTX` 不是「另一種頁排列」，而是**同一套 type-1 頁機制打包多個子索引（order）**：

```text
page 0..3 : 連續 4 頁，各為一個完整的 NTX 式 header
            （各自的 key expression、root offset、item/key size、max_keys）
page 4..  : 其餘每一頁恰屬於其中一棵 B-tree，
            由該 order 的 root 經 type-1 child pointer 可達；
            頁內部排列與上節 type 1 完全相同
```

header offset 2 的值（`.NTX`＝1、`.MTX`＝4）與實際連續 header 頁數在全部樣本一致，
解讀為「檔內 order 數」而非頁格式版本。兩個 `.MTX` 的 order 與所屬表：

| 檔案 | 所屬表 | 4 個 order 的 key expression |
|---|---|---|
| `TMBL.MTX` | `.D21`（經界線） | `STR(LIN_TOP,5)`／`STR(LIN_MID,5)`／`STR(LIN_BOT,5)`／三者串接（key 15） |
| `LINETMBL.MTX` | `.D29`（參考線段） | `LIN_TOP`／`LIN_MID`／`LIN_BOT`（原生 C(10) 欄位，左靠齊）／三者串接（key 30） |

驗證（`tools/verify_ntx_structure.py` 之 `check_mtx`，BA0001＋BA0002 雙樣本）：

- 16 棵樹（2 檔 × 2 段 × 4 order）共 **57,572 筆 entry 逐筆解碼、回查 `.Dxx`
  記錄欄位值，零筆不符**（BA0002：D21 4,027、D29 2,614；BA0001：D21 4,569、D29 3,183）。
- 每棵樹的 entry 數＝所屬表記錄數，record number 與 1..N **一一對應**（零重複、零遺漏）。
- 中序走訪 key 全數非遞減（**零逆序**），child pointer 全數合法。
- **頁覆蓋完整**：4 header 頁＋各樹頁＝全檔頁數，零未歸戶、零跨樹共用。
- 字元 key 直接存欄位原文左靠齊補空白至 DBF 欄寬；數值 key 依 `STR(v,w)` 右靠齊。

先前「近 70% 不符」（BA0002 14,060 筆中 9,807 筆）係把 4 棵樹的頁全當成單一
LIN_TOP 樹解讀所致；該對照仍保留在工具與測試中，證明 `.MTX` 不是單一扁平樹。

可重跑：

```powershell
& 'C:\Users\BASS000025\AppData\Local\Programs\Python\Python314\python.exe' tools/verify_ntx_structure.py
```

## 全部 11 個索引與 .Dxx 表的對應關係（已確認）

先前只逐一確認過 3 個索引（COORDS.NTX→D14、LAND_N.NTX→D11、TMBL.MTX/LINETMBL.MTX→D21/D29）。
其餘 7 個 `.NTX` 從未拿真實資料驗證過所屬表，只能從欄位名猜。`tools/verify_all_indexes_vs_dxx.py`
補上這一步：**不假設**歸屬，而是把每個索引的 key expression 對「每一張欄位名相容的 `.Dxx`/`.D2x`
表」都試著解碼比對，只有零誤差、record number 與 1..N 一一對應的表才算贏家。跨 **BA0001／BA0002／
BA0338** 三份有真實資料的樣本交叉確認，結論如下：

| 索引檔 | 所屬表 | Key expression | 排除的候選 |
|---|---|---|---|
| `BOUNDARY.NTX` | `.D13`（地號界址檔） | `STR(O_SECTION,4)+STR(O_PARCEL,4)+STR(O_PARCEL_E,4)` | `.D12`、`.D2B` |
| `CONTROL.NTX` | `.D20`（私有圖根補點） | `CTL_NAME` | — |
| `COORDS.NTX` | `.D14`（界址坐標檔） | `STR(COT_NUMBER,5)+STR(COT_REF,2)` | `.D2C` |
| `DIV_MER.NTX` | `.D15`（分割合併關係檔） | `STR(SECTION_O,4)+STR(PAR_O_M,4)+STR(PAR_O_C,4)` | `.D11` |
| `DM_INQ.NTX` | `.D15` | `STR(SEC_DM,4)+STR(DIV_MER_M,4)+STR(DIV_MER_C,4)` | （僅 D15 有此欄位） |
| `IN_PAR.NTX` | `.D12`（地中地關係檔，子宗地側） | `STR(I_SECTION,4)+STR(I_PARCEL,4)+STR(I_PARCEL_E,4)` | （僅 D12 有此欄位） |
| `LAND_N.NTX` | `.D11`（宗地資料檔，新編號） | `STR(SECTION_N,4)+STR(PAR_N_M,4)+STR(PAR_N_C,4)` | — |
| `LAND_O.NTX` | `.D11`（舊編號欄位，同一張表） | `STR(SECTION_O,4)+STR(PAR_O_M,4)+STR(PAR_O_C,4)` | `.D15` |
| `LINETMBL.MTX`（4 order） | `.D29`（參考線段檔） | `LIN_TOP`／`LIN_MID`／`LIN_BOT`／三者串接 | `.D21`、`.D2D` |
| `ON_PAR.NTX` | `.D12`（父宗地側） | `STR(O_SECTION,4)+STR(O_PARCEL,4)+STR(O_PARCEL_E,4)` | `.D13`、`.D2B` |
| `TMBL.MTX`（4 order） | `.D21`（經界線資料檔） | `STR(LIN_TOP,5)`／`STR(LIN_MID,5)`／`STR(LIN_BOT,5)`／三者串接 | `.D29`、`.D2D` |

值得注意的兩個先前未定案的關係：

- **`CONTROL.NTX` → `.D20`**：BA0001／BA0002 的 `.D20` 都是空表，只能驗到「空對空」；直到
  BA0338（`.D20` 有 530 筆真實資料）才第一次用非空資料正向確認，530 筆零誤差。
- **`LAND_O.NTX`／`DIV_MER.NTX`**：欄位名（`SECTION_O`／`PAR_O_M`／`PAR_O_C`）容易誤會是指向
  舊地籍圖快照表，但實測 `LAND_O.NTX` 確認指向 `.D11`（同一張表的舊編號欄位），`DIV_MER.NTX`
  指向 `.D15`；兩者都明確**排除** `.D15`／`.D11` 彼此誤配的可能。

### `.D2B`／`.D2C`／`.D2D`（舊地籍圖快照）沒有任何索引指向它們

`.D2B`／`.D2C`／`.D2D` 與 `.D13`／`.D14`／`.D21` 欄位名完全相同（同一 schema 的重測前快照），
是最容易被誤判的候選。上表每個共用欄位名的索引都實際拿它們做過解碼比對——**在全部測過的樣本
裡，`.D2B`／`.D2C`／`.D2D` 從未贏過**（record 數對不上、key 值系統性不符，不是隨機誤差）。結論：
NTX/MTX 只索引「現行」的 D1x/D20/D29 資料，`.D2B`/`.D2C`/`.D2D` 是唯讀歷史快照，沒有索引維護它們。

`.D02`（NECSYS 控制點）、`.D10`、`.D22`、`.D23`、`.D25` 同樣沒有任何索引的 key expression
涉及其欄位——這些表在這套系統裡本來就不透過 NTX/MTX 查詢。

可重跑（含每個索引 vs. 每個候選表的完整比對明細）：

```powershell
& 'C:\Users\BASS000025\AppData\Local\Programs\Python\Python314\python.exe' tools/verify_all_indexes_vs_dxx.py
```

結果見 `analysis/symbol_recovery/all_indexes_vs_dxx.json`。

## 索引與資料表「失步」的真實案例（BA0338／BA0762）

歸屬關係確認之後，同一套工具在兩份樣本上意外發現兩種不同的失步模式，值得記錄：

- **BA0762：索引整批從未建立**。全部 11 個索引 header 解碼完全正常，但每一棵樹的
  root page `used_count = 0`——對非空的 `.D13`/`.D14`/`.D21`/`.D20` 等表完全没有任何項目。
  這與 `docs/project_status.md`「Known Issues」裡獨立做的 D14 突變測試發現（BA0762 的
  `COORDS.NTX` 對 3,393 筆現存 D14 記錄同樣是空的）互相印證：這份樣本的索引是系統性地
  從未建立，不是某個索引個別的解碼錯誤。
- **BA0338：索引存在但鍵值局部過期**。`BOUNDARY.NTX` 對 `.D13` 的 1,559 筆記錄
  **每一筆都還有對應的索引項**（record number 一一對應，零遺漏、零重複），但其中約半數
  （822／1,559）的 key 文字已經跟現在 `.D13` 記錄的 `O_SECTION`/`O_PARCEL`/`O_PARCEL_E`
  對不上。`LAND_N.NTX` 更極端：1,325 筆全部的 key 文字都不符（但 record number 仍全數對應），
  符合「新地號在重測過程中整批重新編號、索引卻沒跟著重建」的情境。這種失步模式跟 BA0762
  不同：B-tree 結構完好、指標正確，只是**搜尋鍵的內容**跟著 Dxx 資料一起漂移了——正是本文件
  最後一節「重建版不得自行寫回 NTX/MTX」規則要防的那種情境的真實範例。

## 安全完整重建流程（已完成副本回歸）

`rebuild/src/nec_rebuild/index_rebuild.py` 依上表 11 個索引對應關係，直接從所屬 DXX 的實體記錄重新產生排序鍵、頁目錄、child pointer、record number 與完整 B-tree；`.MTX` 的 4 個 order 各自重建後放入同一檔案。此流程不沿用舊樹拓撲、不使用 free-page list，也不執行尚未確認的逐頁 split/merge。

安全順序固定為：記憶體建立全部候選 → 逐筆／逐頁／全 record-number coverage 驗證 → 再次確認 DXX 與原索引 hash 未變 → 保存 11 個原檔與 manifest → 同磁碟 `os.replace` 逐檔提交。提交中任何例外會用保留備份回復已替換檔；程序被強制中止後可用 `--recover` 重做完整復原。預設只 dry-run，`test_datasets` 外套用必須另加 `--allow-source-data`。

```powershell
& 'C:\Users\BASS000025\AppData\Local\Programs\Python\Python314\python.exe' tools/rebuild_indexes.py --dataset test_datasets/BA0762
& 'C:\Users\BASS000025\AppData\Local\Programs\Python\Python314\python.exe' tools/rebuild_indexes.py --dataset test_datasets/BA0762 --apply
& 'C:\Users\BASS000025\AppData\Local\Programs\Python\Python314\python.exe' tools/rebuild_indexes.py --dataset test_datasets/BA0762 --recover test_datasets/BA0762/.index-rebuild-backups/<run-id>
```

副本測試涵蓋全部 11 檔／17 order、BA0762 原本空樹的完整建立、獨立讀取器逐筆比對、提交前故障、替換第 5 檔後故障自動 rollback，以及從保留交易備份復原。來源工作段不在測試中寫入。

## 尚未確認

- page 內的空頁鏈（free page list，header offset 8 疑似其起點、樣本全為 0）與刪除後的目錄回收規則。
- 寫入鎖、版本更新、page split/merge（`FUN_009e33d8` 等候選函式的確切觸發門檻）與 crash recovery 規則——這些是執行期行為，靜態反編譯無法確認，需要動態驗證（見 `docs/dynamic_analysis_plan.md`）。

讀取與完整重建路徑（NTX 與 MTX，含全部 11 個索引對應哪張表）已完成副本驗證；但原版 EXE 尚未在隔離環境實際開啟新建索引，所以目前只宣告「重建版驗證器相容」，不宣告原版程式完全相容。正式來源段仍應先 dry-run、保留工作段備份並安排原版開啟驗收。
