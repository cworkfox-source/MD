# SKILL: Taiwan Cadastral BNP/COA/PAR Parser Specification
---
name: taiwan-cadastral-bnp-coa-par-parser
description: Parse and reconstruct Taiwan land cadastral files (BNP boundary sequence, COA boundary coordinates, and PAR parcel attributes) into WKT, GeoJSON, and database-ready structures.
---

# 台灣地籍圖資格式（BNP/COA/PAR）解析與重構規範 (AI Agent & 開發者通用指南)

本文件定義了台灣地政司「圖解區」與「數值區」原始地籍圖資檔案（BNP、COA、PAR）的讀取與多邊形重構邏輯。任何開發程式或 AI 代理人 (Coding Agent) 只要遵循本指南，皆能準確解析此三種檔案並還原出封閉多邊形。

---

## 1. 地籍三檔關係與讀取順序

台灣地籍圖原始圖資以「一地段一組檔」方式儲存：
- **`.COA` (界址點座標檔)**：存有點號與 Y 座標、X 座標。
- **`.BNP` (界址點序列檔)**：存有地號所對應的點號序列（用以組成多邊形）。
- **`.PAR` (地號面積屬性檔)**：存有地號登記面積、計算面積以及標籤文字在地圖上的放置座標。

### 📌 解析順序與組裝邏輯
1. **第一步**：讀取並解析 **`.COA`**，以 `地段代碼_點號` 為唯一的 Key，將點號對應到 (X, Y) 座標。
2. **第二步**：讀取並解析 **`.PAR`**，以 `8碼地號`（母號 4 碼 + 子號 4 碼）為 Key，收集登記面積、計算面積及中心標籤點。
3. **第三步**：讀取並解析 **`.BNP`**，以 `8碼地號` 為 Key，還原點號序列。
4. **第四步**：將 **`.BNP` 的點號序列** 去 **`.COA`** 查出座標。如遇點號間有 `+` 或 `-` 的符號，進行圓弧插值。最後，將序列頭尾閉合，輸出為 WKT Polygon 或 GeoJSON。

---

## 2. 檔案格式精要與注意事項

### 2.1 座標系統與 X/Y 對調 (Critical)
1. **X、Y 的判斷**：COA 檔案中通常為 `Y 座標在前、X 座標在後`。
   - **TWD97 座標特徵**：橫距 X 通常介於 `150,000` 到 `350,000` 之間；縱距 Y 通常介於 `2,550,000` 到 `2,800,000` 之間。
   - **程式防錯機制**：若讀取到的數值 `A > B`，則 A 必為 Y 座標（縱距），B 必為 X 座標（橫距）。
2. **TWD67 座標平移**：若圖資為 TWD67 系統，直接轉換至 TWD97 可套用全台平均經驗值修正：
   - $X_{TWD97} \approx X_{TWD67} + 828.0\text{ 公尺}$
   - $Y_{TWD97} \approx Y_{TWD67} - 207.0\text{ 公尺}$

### 2.2 BNP 跨行序列合併 (Multiline Merging)
- 若某地號的界址點過多，BNP 會將資料拆成多列儲存。
- 每行前 8 碼固定寬度（前 4 碼母號、次 4 碼子號）。後面為 `列序號`、`點數`、`點號序列`。
- **程式重構邏輯**：必須收集相同（母號, 子號）的所有行，依照 `列序號` 由小到大排序後，再行對接合併。

### 2.3 弧形邊界處理 (Arc Notation)
- 當圖解區地籍邊界為圓弧時，BNP 會使用 `A+B` 或 `A-B` 的標記（如 `878+6433`）。
- 這代表從點號 `878`（起點）連接到下一點（終點）之間，邊界是一條通過點號 `6433`（弧中點）的圓弧。
- **重構算法**：
  1. 使用三點座標 $P_{start}$、$P_{mid}$、$P_{end}$，推導出圓心 $(U_x, U_y)$ 與半徑 $R$。
  2. 計算三個點相對於圓心的極角（$\theta_{start}$, $\theta_{mid}$, $\theta_{end}$）。
  3. 依順時針或逆時針方向，在角弧區間內進行等分插值（通常插 10 至 15 個點），將插值點依序插入多邊形頂點序列中。

---

## 3. 通用 Python 實作範本 (`bnp_coa_par_parser.py`)

以下是完全自包含 (Self-contained) 且生產就緒的 Python 類別，可直接載入任何專案。

```python
# -*- coding: utf-8 -*-
import re
import math
import os

class BnpCoaParParser:
    def __init__(self, section_id, crs_type='TWD97', offset_x=0.0, offset_y=0.0, scale=1000):
        self.section_id = str(section_id).strip().upper().replace("BA", "")
        self.crs_type = crs_type.upper()
        self.offset_x = float(offset_x)
        self.offset_y = float(offset_y)
        self.scale = scale
        self.area_type = "數值區" if len(self.section_id) == 4 else "圖解區"
        self.coa_points = {}
        self.bnp_parcels = {}
        self.par_data = {}

    @staticmethod
    def _read_lines(filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Missing file: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.readlines()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='big5', errors='ignore') as f:
                return f.readlines()

    @staticmethod
    def format_parcel_no(m, c):
        return f"{int(m):04d}{int(c):04d}"

    def parse_coa(self, file_or_lines):
        lines = self._read_lines(file_or_lines) if isinstance(file_or_lines, str) else file_or_lines
        pattern = re.compile(r"(2\d{6}\.\d+)\s*([1-3]\d{5}\.\d+)")
        if lines:
            parts = lines[0].strip().split()
            if len(parts) >= 3:
                try: self.scale = int(parts[2])
                except ValueError: pass
        for line in lines[1:]:
            parts = line.strip().split()
            if not parts: continue
            pid = f"{self.section_id}_{parts[0]}"
            match = pattern.search(line)
            if match:
                y, x = float(match.group(1)), float(match.group(2))
                self.coa_points[pid] = (x + self.offset_x, y + self.offset_y)
            else:
                nums = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", line)
                if len(nums) >= 3:
                    v1, v2 = float(nums[-2]), float(nums[-1])
                    self.coa_points[pid] = (min(v1, v2) + self.offset_x, max(v1, v2) + self.offset_y)
        return self.coa_points

    def parse_bnp(self, file_or_lines):
        lines = self._read_lines(file_or_lines) if isinstance(file_or_lines, str) else file_or_lines
        temp = {}
        arc_pattern = re.compile(r"^(\d+)([\+\-])(\d+)$")
        for line in lines[1:]:
            if len(line) < 10: continue
            raw_m, raw_c = line[0:4].strip(), line[4:8].strip()
            if not raw_m.isdigit(): continue
            rest = line[8:].split()
            if len(rest) < 2: continue
            seq = int(rest[0])
            parsed = []
            for t in rest[2:]:
                m = arc_pattern.match(t)
                if m:
                    parsed.append({'id': f"{self.section_id}_{m.group(1)}", 'arc_mid': f"{self.section_id}_{m.group(3)}"})
                else:
                    clean = t.replace('+', '').replace('-', '')
                    if clean: parsed.append({'id': f"{self.section_id}_{clean}"})
            temp.setdefault((raw_m, raw_c), []).append((seq, parsed))
        
        for (m, c), rows in temp.items():
            rows.sort(key=lambda r: r[0])
            pts = []
            for _, r_pts in rows: pts.extend(r_pts)
            self.bnp_parcels[self.format_parcel_no(m, c)] = pts
        return self.bnp_parcels

    def parse_par(self, file_or_lines):
        lines = self._read_lines(file_or_lines) if isinstance(file_or_lines, str) else file_or_lines
        coord_pattern = re.compile(r"0?(2\d{6}\.\d+)\s*([1-2]\d{5}\.\d+)")
        for line in lines[1:]:
            if len(line) < 40: continue
            raw_m, raw_c = line[0:4].strip(), line[4:8].strip()
            if not raw_m or not raw_m.isdigit(): continue
            reg = float(re.sub(r'[^\d.]', '', line[12:22].strip())) if line[12:22].strip() else 0.0
            calc = float(re.sub(r'[^\d.]', '', line[30:40].strip())) if line[30:40].strip() else 0.0
            match = coord_pattern.search(line[40:])
            lx, ly = (float(match.group(2)) + self.offset_x, float(match.group(1)) + self.offset_y) if match else (None, None)
            self.par_data[self.format_parcel_no(raw_m, raw_c)] = {'reg': reg, 'calc': calc, 'label_x': lx, 'label_y': ly}
        return self.par_data

    def build_polygons(self, arc_steps=15):
        results = {}
        for pno, pt_objs in self.bnp_parcels.items():
            coords = []
            n = len(pt_objs)
            if n < 3: continue
            for i in range(n):
                curr = pt_objs[i]
                next_pt = pt_objs[(i + 1) % n]
                xy = self.coa_points.get(curr['id'])
                if not xy: continue
                coords.append(xy)
                if 'arc_mid' in curr:
                    mid_xy = self.coa_points.get(curr['arc_mid'])
                    next_xy = self.coa_points.get(next_pt['id'])
                    if mid_xy and next_xy:
                        # 弧線插值邏輯
                        center, radius = self._get_circle_center(xy, mid_xy, next_xy)
                        if center:
                            arc_pts = self._get_arc_points(xy, mid_xy, next_xy, center, radius, arc_steps)
                            coords.extend(arc_pts[:-1])
            if len(coords) >= 3:
                if coords[0] != coords[-1]: coords.append(coords[0])
                attrs = self.par_data.get(pno, {'reg': 0.0, 'calc': 0.0, 'label_x': None, 'label_y': None})
                results[pno] = {
                    'coords': coords,
                    'wkt': f"POLYGON(({','.join(f'{p[0]} {p[1]}' for p in coords)}))",
                    'reg_area': attrs['reg'],
                    'calc_area': attrs['calc'],
                    'label_x': attrs['label_x'],
                    'label_y': attrs['label_y']
                }
        return results

    def _get_circle_center(self, p1, p2, p3):
        x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
        D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(D) < 1e-9: return None, None
        Ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / D
        Uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / D
        return (Ux, Uy), math.sqrt((Ux - x1)**2 + (Uy - y1)**2)

    def _get_arc_points(self, p_start, p_mid, p_end, center, radius, steps):
        ang_start = math.atan2(p_start[1] - center[1], p_start[0] - center[0])
        ang_mid = math.atan2(p_mid[1] - center[1], p_mid[0] - center[0])
        ang_end = math.atan2(p_end[1] - center[1], p_end[0] - center[0])
        if ang_start < 0: ang_start += 2 * math.pi
        if ang_mid < 0: ang_mid += 2 * math.pi
        if ang_end < 0: ang_end += 2 * math.pi
        
        def interp(a1, a2, n):
            diff = a2 - a1
            if diff > math.pi: diff -= 2 * math.pi
            elif diff < -math.pi: diff += 2 * math.pi
            return [(center[0] + radius * math.cos(a1 + diff * (i/n)), center[1] + radius * math.sin(a1 + diff * (i/n))) for i in range(1, n + 1)]
            
        pts = []
        pts.extend(interp(ang_start, ang_mid, max(1, steps // 2)))
        pts.extend(interp(ang_mid, ang_end, max(1, steps // 2)))
        return pts
```

---

## 4. 通用 JavaScript 實作範本 (`BnpCoaParParser.js`)

適合直接用於 Web 網頁端、Node.js 或是 Leaflet 等前端圖資展示環境。

```javascript
class BnpCoaParParser {
    constructor(sectionId, options = {}) {
        this.sectionId = sectionId.replace("BA", "").trim().toUpperCase();
        this.offsetX = options.offsetX || 0;
        this.offsetY = options.offsetY || 0;
        this.scale = options.scale || 1000;
        this.areaType = this.sectionId.length === 4 ? "數值區" : "圖解區";
        this.points = {};
        this.parcels = {};
        this.attributes = {};
    }

    static formatParcelNo(m, c) {
        const pm = String(parseInt(m, 10) || 0).padStart(4, '0');
        const pc = String(parseInt(c, 10) || 0).padStart(4, '0');
        return pm + pc;
    }

    parseCOA(text) {
        const lines = text.split(/\r?\n/);
        if (lines.length === 0) return;
        const header = lines[0].trim().split(/\s+/);
        if (header.length >= 3) {
            this.scale = parseInt(header[2], 10) || this.scale;
        }

        const regex = /(2\d{6}\.\d+)\s*([1-3]\d{5}\.\d+)/;
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            const parts = line.split(/\s+/);
            if (parts.length === 0 || !parts[0]) continue;

            const pid = `${this.sectionId}_${parts[0]}`;
            const match = regex.exec(line);
            if (match) {
                const y = parseFloat(match[1]) + this.offsetY;
                const x = parseFloat(match[2]) + this.offsetX;
                this.points[pid] = [x, y];
            } else {
                const nums = line.match(/[-+]?\d*\.\d+|[-+]?\d+/g);
                if (nums && nums.length >= 3) {
                    const v1 = parseFloat(nums[nums.length - 2]);
                    const v2 = parseFloat(nums[nums.length - 1]);
                    const y = Math.max(v1, v2) + this.offsetY;
                    const x = Math.min(v1, v2) + this.offsetX;
                    this.points[pid] = [x, y];
                }
            }
        }
    }

    parseBNP(text) {
        const lines = text.split(/\r?\n/);
        const temp = {};
        const arcRegex = /^(\d+)([\+\-])(\d+)$/;

        for (let i = 1; i < lines.length; i++) {
            const line = lines[i];
            if (line.length < 10) continue;

            const rawM = line.substring(0, 4).trim();
            const rawC = line.substring(4, 8).trim();
            if (!/^\d+$/.test(rawM)) continue;

            const rest = line.substring(8).trim().split(/\s+/);
            if (rest.length < 2) continue;

            const seq = parseInt(rest[0], 10);
            const parsed = [];

            for (let j = 2; j < rest.length; j++) {
                const token = rest[j];
                const match = arcRegex.exec(token);
                if (match) {
                    parsed.push({
                        id: `${this.sectionId}_${match[1]}`,
                        arcMid: `${this.sectionId}_${match[3]}`
                    });
                } else {
                    const clean = token.replace(/[\+\-]/g, '');
                    if (clean) {
                        parsed.push({ id: `${this.sectionId}_${clean}` });
                    }
                }
            }
            const key = `${rawM}-${rawC}`;
            if (!temp[key]) temp[key] = [];
            temp[key].push({ seq, parsed });
        }

        for (const [key, rows] of Object.entries(temp)) {
            rows.sort((a, b) => a.seq - b.seq);
            const allPts = [];
            rows.forEach(r => allPts.push(...r.parsed));
            const parts = key.split('-');
            const stdNo = BnpCoaParParser.formatParcelNo(parts[0], parts[1]);
            this.parcels[stdNo] = allPts;
        }
    }

    parsePAR(text) {
        const lines = text.split(/\r?\n/);
        const regex = /0?(2\d{6}\.\d+)\s*([1-2]\d{5}\.\d+)/;

        for (let i = 1; i < lines.length; i++) {
            const line = lines[i];
            if (line.length < 40) continue;

            const rawM = line.substring(0, 4).trim();
            const rawC = line.substring(4, 8).trim();
            if (!rawM || !/^\d+$/.test(rawM)) continue;

            const regStr = line.substring(12, 22).replace(/[^\d.]/g, '');
            const calcStr = line.substring(30, 40).replace(/[^\d.]/g, '');
            const reg = parseFloat(regStr) || 0;
            const calc = parseFloat(calcStr) || 0;

            const match = regex.exec(line.substring(40));
            let lx = null, ly = null;
            if (match) {
                ly = parseFloat(match[1]) + this.offsetY;
                lx = parseFloat(match[2]) + this.offsetX;
            }

            const stdNo = BnpCoaParParser.formatParcelNo(rawM, rawC);
            this.attributes[stdNo] = { reg, calc, lx, ly };
        }
    }

    buildPolygons(arcSteps = 15) {
        const results = {};
        for (const [pno, ptObjs] of Object.entries(this.parcels)) {
            const coords = [];
            const n = ptObjs.length;
            if (n < 3) continue;

            for (let i = 0; i < n; i++) {
                const curr = ptObjs[i];
                const nextPt = ptObjs[(i + 1) % n];
                const xy = this.points[curr.id];
                if (!xy) continue;

                coords.push(xy);

                if (curr.arcMid) {
                    const midXy = this.points[curr.arcMid];
                    const nextXy = this.points[nextPt.id];
                    if (midXy && nextXy) {
                        const arcPts = this._interpolateArc(xy, midXy, nextXy, arcSteps);
                        coords.push(...arcPts.slice(0, -1));
                    }
                }
            }

            if (coords.length >= 3) {
                if (coords[0][0] !== coords[coords.length - 1][0] || coords[0][1] !== coords[coords.length - 1][1]) {
                    coords.push(coords[0]);
                }
                const attr = this.attributes[pno] || { reg: 0, calc: 0, lx: null, ly: null };
                results[pno] = {
                    coords: coords,
                    regArea: attr.reg,
                    calcArea: attr.calc,
                    labelX: attr.lx,
                    labelY: attr.ly
                };
            }
        }
        return results;
    }

    _interpolateArc(p1, p2, p3, steps) {
        const x1 = p1[0], y1 = p1[1];
        const x2 = p2[0], y2 = p2[1];
        const x3 = p3[0], y3 = p3[1];
        const D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2));
        if (Math.abs(D) < 1e-9) return [p2, p3];

        const Ux = ((x1*x1 + y1*y1) * (y2 - y3) + (x2*x2 + y2*y2) * (y3 - y1) + (x3*x3 + y3*y3) * (y1 - y2)) / D;
        const Uy = ((x1*x1 + y1*y1) * (x3 - x2) + (x2*x2 + y2*y2) * (x1 - x3) + (x3*x3 + y3*y3) * (x2 - x1)) / D;
        const radius = Math.sqrt((Ux - x1)*(Ux - x1) + (Uy - y1)*(Uy - y1));

        let a1 = Math.atan2(y1 - Uy, x1 - Ux);
        let a2 = Math.atan2(y2 - Uy, x2 - Ux);
        let a3 = Math.atan2(y3 - Uy, x3 - Ux);
        if (a1 < 0) a1 += 2 * Math.PI;
        if (a2 < 0) a2 += 2 * Math.PI;
        if (a3 < 0) a3 += 2 * Math.PI;

        const interp = (start, end, n) => {
            let diff = end - start;
            if (diff > Math.PI) diff -= 2 * Math.PI;
            else if (diff < -Math.PI) diff += 2 * Math.PI;
            const pts = [];
            for (let i = 1; i <= n; i++) {
                const angle = start + diff * (i / n);
                pts.push([Ux + radius * Math.cos(angle), Uy + radius * Math.sin(angle)]);
            }
            return pts;
        };

        const half = Math.max(1, Math.floor(steps / 2));
        const pts = [];
        pts.push(...interp(a1, a2, half));
        pts.push(...interp(a2, a3, half));
        return pts;
    }
}
```

---

## 5. 給 AI Coding Agent 的提示詞調用指南 (Prompting Guide)

當你需要其他 LLM / Coding Agent 處理地籍三檔時，可以提供以下 Prompt：

> **[Prompt範本]**
> 請使用 `taiwan-cadastral-bnp-coa-par-parser` 規格。
> 1. 解析指定地段的 `.COA`，提取界址點，注意 X/Y 對調（X 在後 Y 在前，若 $Y < 1,000,000$ 且 $X > 1,000,000$ 則須對調）。
> 2. 解析 `.PAR`，對登記與計算面積數字進行清洗，僅保留小數與數字。
> 3. 解析 `.BNP`，需將相同地號母子號的分散列按序號排序並合併。
> 4. 若遇到 `+` 或 `-` 的點號連結（弧形標記），使用三點共圓（起點、弧中點、終點）演算法計算圓弧插值。
> 5. 輸出包含登記面積與計算面積的 GeoJSON 多邊形。
