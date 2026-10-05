#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重測原始檔讀取器：純標準函式庫，可直接複製到任何專案使用。

涵蓋「地籍圖重測資料處理系統（視窗版）」四類原始檔：
  1. 段目錄資料檔  .D10~.D2D（dBASE III）、.D25（79 byte 自訂二進位）
  2. 重測輸入交換檔 .PTM / .BNI / .CNT / .INN
  3. 複丈系統交換檔 .PAR / .BNP / .COA / .RCO
  4. 測量輸入檔    .MAC / .CTL

欄位語意的權威來源是 docs/file_formats/<副檔名>.md；本檔只實作讀取。
本檔**只讀不寫**，任何情況都不會修改來源檔案。

用法：
    python read_resurvey.py <段目錄或單一檔案>
    python read_resurvey.py <段目錄> --parcel 755-365-2
    python read_resurvey.py <段目錄> --point 6857
    python read_resurvey.py <段目錄> --verify-areas [--limit 20]
    python read_resurvey.py <檔案> --dump [--limit 20]
"""

from __future__ import annotations

import argparse
import math
import re
import struct
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

ENCODING = "cp950"           # 舊系統一律 Big5/CP950
Point = tuple[float, float]  # 一律 (X, Y)；注意檔案內是 Y 在前
ParcelKey = tuple[int, int, int]  # (段號, 母號, 子號)

DBF_FIELD_DESC_SIZE = 32
D25_RECORD_SIZE = 79
D25_TRAILER_SIZE = 32
MAX_POINTS_PER_EXCHANGE_RECORD = 11
_CONFIRMED_NAME = re.compile(r"^(?P<number>\d{1,5})(?:\.(?P<ref>\d{1,2}))?$")
_INTEGRATED_HEADER = re.compile(r"^[A-Za-z]{2}\d")


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------


def _int(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _float(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding=ENCODING, errors="replace").splitlines()


# ---------------------------------------------------------------------------
# 1a. dBASE III：.D10~.D2D（.D25 除外）與其 .Bxx 備份
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DbfField:
    name: str
    type: str
    length: int
    decimals: int


@dataclass(frozen=True)
class DbfInfo:
    version: int
    record_count: int
    header_length: int
    record_length: int
    fields: tuple[DbfField, ...]

    def size_check(self, file_size: int) -> bool:
        """header + n × record 應等於檔案大小（可多 1 byte 的 0x1A 檔尾）。"""

        expected = self.header_length + self.record_count * self.record_length
        return file_size in (expected, expected + 1)


def is_dbf(path: Path) -> bool:
    """辨識 dBASE III。

    不看檔頭日期：本系統寫入的 year byte 恆為 0x7E，不合 `年-1900` 慣例
    （見 docs/file_formats/D10.md）。改以「header + n × record ≒ 檔案大小」判定。
    """

    with path.open("rb") as handle:
        head = handle.read(12)
    if len(head) < 12 or head[0] not in (0x03, 0x83):
        return False
    record_count, header_length, record_length = struct.unpack_from("<IHH", head, 4)
    if header_length < 33 or record_length < 1:
        return False
    expected = header_length + record_count * record_length
    return path.stat().st_size in (expected, expected + 1)


def read_dbf_info(path: Path) -> DbfInfo:
    data = path.read_bytes()
    version = data[0]
    record_count, header_length, record_length = struct.unpack_from("<IHH", data, 4)
    fields: list[DbfField] = []
    offset = 32
    while offset + DBF_FIELD_DESC_SIZE <= len(data) and data[offset] != 0x0D:
        block = data[offset : offset + DBF_FIELD_DESC_SIZE]
        name = block[0:11].split(b"\x00")[0].decode("ascii", "replace").strip()
        fields.append(DbfField(name, chr(block[11]), block[16], block[17]))
        offset += DBF_FIELD_DESC_SIZE
    return DbfInfo(version, record_count, header_length, record_length, tuple(fields))


def _decode_dbf_value(raw: bytes, field: DbfField):
    stripped = raw.decode(ENCODING, "replace").strip()
    if field.type == "C":
        return stripped
    if field.type == "L":
        upper = stripped.upper()
        if upper in ("T", "Y"):
            return True
        if upper in ("F", "N"):
            return False
        return None
    if field.type == "D":
        return stripped or None
    if field.type == "N":
        if not stripped:
            return None
        try:
            return float(stripped) if field.decimals else int(stripped)
        except ValueError:
            return None
    return stripped


def read_dbf(path: Path, *, keep_deleted: bool = False):
    """逐筆產出 dict。已刪除列（第 0 byte = '*'）預設略過。"""

    info = read_dbf_info(path)
    with path.open("rb") as handle:
        handle.seek(info.header_length)
        for _ in range(info.record_count):
            record = handle.read(info.record_length)
            if len(record) < info.record_length:
                break
            deleted = record[0:1] == b"*"
            if deleted and not keep_deleted:
                continue
            row: dict = {}
            offset = 1
            for field in info.fields:
                row[field.name] = _decode_dbf_value(
                    record[offset : offset + field.length], field
                )
                offset += field.length
            if keep_deleted:
                row["_deleted"] = deleted
            yield row


# ---------------------------------------------------------------------------
# 1b. .D25：非 dBASE，79 byte 固定二進位＋32 byte NULLTAB 收尾
# ---------------------------------------------------------------------------


def _d25_name(raw: bytes) -> str:
    return raw.split(b"\x00")[0].decode("ascii", "replace").strip()


def read_d25(path: Path) -> list[dict]:
    data = path.read_bytes()
    count = (len(data) - D25_TRAILER_SIZE) // D25_RECORD_SIZE
    if count < 0 or len(data) != count * D25_RECORD_SIZE + D25_TRAILER_SIZE:
        count = len(data) // D25_RECORD_SIZE  # 檔尾不符預期時仍讀完整記錄
    rows: list[dict] = []
    for index in range(count):
        record = data[index * D25_RECORD_SIZE : (index + 1) * D25_RECORD_SIZE]
        if len(record) < D25_RECORD_SIZE:
            break
        rows.append(
            {
                "seq": struct.unpack_from("<I", record, 4)[0],
                "name1": _d25_name(record[32:39]),
                "name2": _d25_name(record[41:48]),
                "name3": _d25_name(record[50:57]),
                "flag60": struct.unpack_from("<d", record, 60)[0],
                "distance": struct.unpack_from("<d", record, 69)[0],
                "tail_ok": record[77:79] == b",*",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 2/3. 交換檔：坐標 .CNT / .COA / .RCO
# ---------------------------------------------------------------------------


def parse_cnt(lines: list[str]) -> tuple[dict[tuple[int, int], Point], dict[str, Point], int]:
    """三種 .CNT 方言共通：以空白切成 點名 / Y / X 即可全部讀出。

    回傳 ((點號, 參考號) -> (X, Y), 控制點名 -> (X, Y), 略過列數)。
    """

    points: dict[tuple[int, int], Point] = {}
    named: dict[str, Point] = {}
    skipped = 0
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            skipped += 1 if line.strip() else 0
            continue
        name, y, x = parts[0], _float(parts[1]), _float(parts[2])
        if y is None or x is None:
            skipped += 1
            continue
        match = _CONFIRMED_NAME.match(name)
        if match is None:
            named[name.upper()] = (x, y)  # 圖根點名如 C326C069
            continue
        points[(int(match.group("number")), int(match.group("ref") or 0))] = (x, y)
    return points, named, skipped


def parse_coa(lines: list[str]) -> tuple[dict[tuple[int, int], Point], int, str]:
    """.COA：整合版（樣本驗證）優先，ⅠⅡ版為未驗證後備。"""

    body = lines[1:] if lines and _INTEGRATED_HEADER.match(lines[0]) else lines
    points: dict[tuple[int, int], Point] = {}
    skipped = 0
    for line in body:
        if len(line) < 37:
            skipped += 1 if line.strip() else 0
            continue
        number, y, x = _int(line[0:5]), _float(line[6:22]), _float(line[22:37])
        if number is None or x is None or y is None or (x == 0.0 and y == 0.0):
            skipped += 1
            continue
        points[(number, 0)] = (x, y)
    if points:
        return points, skipped, "COA(整合版)"
    for order, line in enumerate(body, start=1):  # ⅠⅡ版：無點號欄，依序推定
        if len(line) < 25:
            continue
        y, x = _float(line[2:14]), _float(line[14:25])
        if x is None or y is None or (x == 0.0 and y == 0.0):
            continue
        points[(order, 0)] = (x, y)
    return points, skipped, "COA(ⅠⅡ版,未經樣本驗證)"


def parse_rco(lines: list[str]) -> dict[tuple[int, int], Point]:
    """.RCO 參考坐標檔（整合版 I5+I2+F11.3+F10.3+A1）。"""

    body = lines[1:] if lines and _INTEGRATED_HEADER.match(lines[0]) else lines
    points: dict[tuple[int, int], Point] = {}
    for line in body:
        if len(line) < 28:
            continue
        number, ref = _int(line[0:5]), _int(line[5:7])
        y, x = _float(line[7:18]), _float(line[18:28])
        if number is None or x is None or y is None:
            continue
        points[(number, ref or 0)] = (x, y)
    return points


# ---------------------------------------------------------------------------
# 2/3. 交換檔：點號序列 .BNI / .BNP
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParcelSequences:
    sequences: "OrderedDict[ParcelKey, list[int]]"
    arc_midpoints: "OrderedDict[ParcelKey, tuple[bool, ...]]"
    skipped: int
    arc_points: int
    source: str


def _parse_fixed_point_tail(tail: str, point_width: int) -> tuple[list[int], list[bool]]:
    """依 A1+I4/I5 固定欄位切點；圓弧記號寫在**下一組**的 A1 欄。"""

    numbers: list[int] = []
    arcs: list[bool] = []
    group_width = point_width + 1
    for offset in range(0, len(tail), group_width):
        group = tail[offset : offset + group_width]
        if len(group) < 2:
            continue
        number = _int(group[1:])
        if not number:
            continue
        numbers.append(number)
        arcs.append(group[0].strip().upper() in {"+", "-", "Y"})
    return numbers, arcs


def _merge_rows(rows) -> tuple[OrderedDict, OrderedDict]:
    """同一宗地的續錄依「序號」由小到大接起來。"""

    merged: OrderedDict[ParcelKey, list[int]] = OrderedDict()
    merged_arcs: OrderedDict[ParcelKey, tuple[bool, ...]] = OrderedDict()
    for key, parts in rows.items():
        numbers: list[int] = []
        arcs: list[bool] = []
        for _sequence, chunk, chunk_arcs in sorted(parts, key=lambda item: item[0]):
            numbers.extend(chunk)
            arcs.extend(chunk_arcs)
        merged[key] = numbers
        merged_arcs[key] = tuple(arcs)
    return merged, merged_arcs


def parse_bnp(lines: list[str]) -> ParcelSequences:
    """.BNP：有 `A2+數字` 標題錄者為整合版（key 是**新地號**）。"""

    if lines and _INTEGRATED_HEADER.match(lines[0]):
        section = _int(lines[0][2:6]) or 0
        rows: OrderedDict = OrderedDict()
        skipped = arcs = 0
        for line in lines[1:]:
            if len(line) < 15:
                skipped += 1 if line.strip() else 0
                continue
            parcel, ext, sequence = _int(line[0:4]), _int(line[4:8]), _int(line[8:11])
            if parcel is None or ext is None or sequence is None:
                skipped += 1
                continue
            numbers, line_arcs = _parse_fixed_point_tail(line[15:], 5)
            arcs += sum(line_arcs)
            rows.setdefault((section, parcel, ext), []).append(
                (sequence, numbers, line_arcs)
            )
        sequences, arc_midpoints = _merge_rows(rows)
        return ParcelSequences(sequences, arc_midpoints, skipped, arcs, "BNP(整合版)")
    return _parse_original_number_layout(lines, "BNP(ⅠⅡ版,未經樣本驗證)")


def parse_bni(lines: list[str]) -> ParcelSequences:
    """.BNI：原地號版面（與複丈ⅠⅡ版 .BNP 相同）。"""

    return _parse_original_number_layout(lines, "BNI")


def _parse_original_number_layout(lines: list[str], label: str) -> ParcelSequences:
    rows: OrderedDict = OrderedDict()
    skipped = arcs = 0
    point_width = 5 if max((len(line) for line in lines), default=0) >= 89 else 4
    for line in lines:
        if len(line) < 23:
            skipped += 1 if line.strip() else 0
            continue
        parcel, ext = _int(line[0:4]), _int(line[4:8])
        section, sequence = _int(line[8:12]), _int(line[12:15])
        if parcel is None or ext is None or section is None or sequence is None:
            skipped += 1
            continue
        declared = _int(line[19:23]) or 0
        expected = min(
            MAX_POINTS_PER_EXCHANGE_RECORD,
            max(0, declared - (sequence - 1) * MAX_POINTS_PER_EXCHANGE_RECORD),
        )
        alternate = 4 if point_width == 5 else 5
        candidates = [
            _parse_fixed_point_tail(line[23:], width)
            for width in (point_width, alternate)
        ]
        numbers, line_arcs = min(
            candidates, key=lambda candidate: abs(len(candidate[0]) - expected)
        )
        arcs += sum(line_arcs)
        rows.setdefault((section, parcel, ext), []).append((sequence, numbers, line_arcs))
    sequences, arc_midpoints = _merge_rows(rows)
    return ParcelSequences(sequences, arc_midpoints, skipped, arcs, label)


# ---------------------------------------------------------------------------
# 2/3. 交換檔：屬性 .PTM / .PAR / .INN
# ---------------------------------------------------------------------------


def parse_ptm(lines: list[str]) -> list[dict]:
    """.PTM 資料錄 51 bytes；原登記面積為**公頃**。"""

    rows: list[dict] = []
    for line in lines:
        if len(line) < 36:
            continue
        rows.append(
            {
                "PAR_O_M": _int(line[0:4]),
                "PAR_O_C": _int(line[4:8]),
                "SECTION_O": _int(line[8:12]),
                "SECTION_N": _int(line[12:16]),
                "POINT_COUNT": _int(line[16:20]),
                "HAS_INNER": _int(line[20:22]),
                "CATEGORY": _int(line[23:25]),
                "AREA_OLD_HA": _float(line[25:36]),
                "GRADE": _int(line[36:38]),
                "INVES": _int(line[38:41]),
                "BELONG": _int(line[41:43]),
                "USING": _int(line[43:45]),
                "HOUSE": _int(line[45:47]),
                "OWNERS": _int(line[47:51]),
            }
        )
    return rows


def parse_par(lines: list[str]) -> tuple[list[dict], str]:
    """.PAR 整合版資料錄 63 bytes；面積為**平方公尺**。"""

    body = lines[1:] if lines and _INTEGRATED_HEADER.match(lines[0]) else lines
    rows: list[dict] = []
    for line in body:
        if len(line) < 40:
            continue
        rows.append(
            {
                "PAR_O_M": _int(line[0:4]),
                "PAR_O_C": _int(line[4:8]),
                "SECTION_O": _int(line[8:12]),
                "AREA_OLD_M2": _float(line[12:22]),
                "PAR_N_M": _int(line[22:26]),
                "PAR_N_C": _int(line[26:30]),
                "AREA_NEW_M2": _float(line[30:40]),
                "CATEGORY": line[40:41].strip(),
                "GRADE": _int(line[41:43]) if len(line) > 41 else None,
                "CENTER_Y": _float(line[43:52]) if len(line) > 43 else None,
                "CENTER_X": _float(line[52:60]) if len(line) > 52 else None,
                "SHEET": _int(line[60:63]) if len(line) > 60 else None,
            }
        )
    return rows, "PAR(整合版)"


def parse_inn(lines: list[str]) -> list[dict]:
    """.INN 新舊地號對照；第 6/7 欄手冊欄名疑為誤植，實作視為新地號。"""

    rows: list[dict] = []
    for line in lines:
        if len(line) < 22:
            continue
        rows.append(
            {
                "PAR_O_M": _int(line[0:4]),
                "PAR_O_C": _int(line[5:9]),
                "SECTION_O": _int(line[9:13]),
                "PAR_N_M": _int(line[14:18]),
                "PAR_N_C": _int(line[18:22]),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 4. 測量輸入檔 .CTL / .MAC
# ---------------------------------------------------------------------------


def parse_ctl(lines: list[str]) -> dict[str, Point]:
    """.CTL 圖根點：資料錄 A8 + F11.3(Y) + F12.3(X)。

    實檔（BA0000／BA0113／DD2138／GW9000）欄位有貼死也有以空白隔開，
    因此先試空白切詞、失敗才退回固定欄寬；第一錄（檔名/代碼標題）自然被略過。
    多出來的第 4 欄（如 `0.000`）不解讀。
    """

    points: dict[str, Point] = {}
    for line in lines:
        parts = line.split()
        name, y, x = None, None, None
        if len(parts) >= 3:
            name, y, x = parts[0], _float(parts[1]), _float(parts[2])
        if (y is None or x is None) and len(line) >= 19:
            name, y, x = line[0:8].strip(), _float(line[8:19]), _float(line[19:31])
        if not name or x is None or y is None:
            continue
        points[name.upper()] = (x, y)
    return points


def parse_mac(lines: list[str]) -> list[dict]:
    """.MAC 批次計算文字檔：切成 LS（光線法）／LB（直線截點）區塊。

    角度為「度.分秒」（12.2345 ＝ 12°23'45"），見 dms_to_degrees()。
    """

    blocks: list[dict] = []
    current: dict | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        head = line.split()[0].upper()
        if head in ("LS", "LB"):
            current = {"kind": head, "rows": []}
            blocks.append(current)
            continue
        if current is None:
            continue
        current["rows"].append(line.replace(",", " ").split())
    return blocks


def dms_to_degrees(value: float | str) -> float:
    """把「度.分秒」（如 293.191 → 293.1910）換算成十進位度。"""

    text = value.strip() if isinstance(value, str) else f"{float(value):.4f}"
    if "." not in text:
        text += ".0000"
    whole, frac = text.split(".", 1)
    frac = (frac + "0000")[:4]
    return int(whole) + int(frac[0:2]) / 60.0 + int(frac[2:4]) / 3600.0


# ---------------------------------------------------------------------------
# 幾何：宗地環重建與面積（含解析式真弧）
# ---------------------------------------------------------------------------


def circle_from_three_points(a: Point, b: Point, c: Point):
    determinant = 2.0 * (
        a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])
    )
    scale = max(math.dist(a, b), math.dist(b, c), math.dist(a, c), 1.0)
    if abs(determinant) <= 1e-14 * scale * scale:
        return None
    a2, b2, c2 = a[0] ** 2 + a[1] ** 2, b[0] ** 2 + b[1] ** 2, c[0] ** 2 + c[1] ** 2
    ux = (a2 * (b[1] - c[1]) + b2 * (c[1] - a[1]) + c2 * (a[1] - b[1])) / determinant
    uy = (a2 * (c[0] - b[0]) + b2 * (a[0] - c[0]) + c2 * (b[0] - a[0])) / determinant
    center = (ux, uy)
    return center, math.dist(center, a)


def arc_signed_area_correction(start: Point, mid: Point, end: Point) -> float:
    """把 start→mid→end 兩段弦換成真弧的**修正量**（加到 shoelace 結果）。"""

    circle = circle_from_three_points(start, mid, end)
    if circle is None:
        return 0.0
    (cx, cy), radius = circle
    start_angle = math.atan2(start[1] - cy, start[0] - cx)
    mid_angle = math.atan2(mid[1] - cy, mid[0] - cx)
    end_angle = math.atan2(end[1] - cy, end[0] - cx)

    def ccw(begin: float, finish: float) -> float:
        return (finish - begin) % math.tau

    direction = 1 if ccw(start_angle, end_angle) >= ccw(start_angle, mid_angle) else -1
    if direction > 0:
        span = ccw(start_angle, mid_angle) + ccw(mid_angle, end_angle)
    else:
        span = ccw(mid_angle, start_angle) + ccw(end_angle, mid_angle)
    signed_span = direction * span
    arc_from_chord = radius * radius * (signed_span - math.sin(signed_span)) / 2.0
    triangle = (
        start[0] * mid[1]
        - mid[0] * start[1]
        + mid[0] * end[1]
        - end[0] * mid[1]
        + end[0] * start[1]
        - start[0] * end[1]
    ) / 2.0
    return arc_from_chord - triangle


def polygon_area(ring: list[Point], arc_midpoints: tuple[bool, ...] = ()) -> float:
    """shoelace；標記為弧中點者以解析式真弧取代兩段弦（單位：平方公尺）。"""

    total = 0.0
    count = len(ring)
    for index in range(count):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % count]
        total += x1 * y2 - x2 * y1
    area = total / 2.0
    if len(arc_midpoints) == count:
        for index, is_midpoint in enumerate(arc_midpoints):
            if is_midpoint:
                area += arc_signed_area_correction(
                    ring[index - 1], ring[index], ring[(index + 1) % count]
                )
    return abs(area)


def read_d13_sequences(path: Path) -> tuple[OrderedDict, OrderedDict]:
    """.D13 → (宗地 -> 點號序列, 宗地 -> 弧中點旗標)。

    同一宗地超過 8 點時**依檔案物理順序**接續多筆記錄（無序號欄），
    直到某筆以 COORD_n = 0 補零為止。
    """

    sequences: OrderedDict[ParcelKey, list[int]] = OrderedDict()
    arcs: OrderedDict[ParcelKey, list[bool]] = OrderedDict()
    for row in read_dbf(path):
        key = (
            int(row.get("O_SECTION") or 0),
            int(row.get("O_PARCEL") or 0),
            int(row.get("O_PARCEL_E") or 0),
        )
        numbers = sequences.setdefault(key, [])
        flags = arcs.setdefault(key, [])
        for index in range(1, 9):
            number = row.get(f"COORD_{index}")
            if not number:
                continue
            numbers.append(int(number))
            flags.append(bool(row.get(f"MIDARC_{index}")))
    return sequences, OrderedDict((key, tuple(value)) for key, value in arcs.items())


def read_d14_points(path: Path) -> tuple[dict[int, Point], dict[tuple[int, int], Point]]:
    """.D14 → (確定點 COT_REF==0 的 點號 -> (X, Y), 全部 (點號, 參考號) -> (X, Y))。"""

    confirmed: dict[int, Point] = {}
    every: dict[tuple[int, int], Point] = {}
    for row in read_dbf(path):
        number = row.get("COT_NUMBER")
        if number is None:
            continue
        ref = int(row.get("COT_REF") or 0)
        x, y = row.get("COT_X"), row.get("COT_Y")
        if x is None or y is None:
            continue
        every[(int(number), ref)] = (float(x), float(y))
        if ref == 0:
            confirmed[int(number)] = (float(x), float(y))
    return confirmed, every


def build_rings(
    sequences: OrderedDict, arcs: OrderedDict, points: dict[int, Point]
) -> tuple[dict[ParcelKey, list[Point]], dict[ParcelKey, str]]:
    """點號序列 + 確定點坐標 → 宗地環；不足 3 點或缺坐標者不產生環。"""

    rings: dict[ParcelKey, list[Point]] = {}
    rejected: dict[ParcelKey, str] = {}
    for key, numbers in sequences.items():
        flags = list(arcs.get(key, ()))
        ring: list[Point] = []
        ring_flags: list[bool] = []
        missing: list[int] = []
        for index, number in enumerate(numbers):
            coordinate = points.get(number)
            if coordinate is None:
                missing.append(number)
                continue
            if ring and coordinate == ring[-1]:
                continue  # 連續重複點只留一個
            ring.append(coordinate)
            ring_flags.append(flags[index] if index < len(flags) else False)
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring.pop()
            ring_flags.pop()
        if missing:
            rejected[key] = f"缺坐標點號 {missing[:5]}{'…' if len(missing) > 5 else ''}"
            continue
        if len(ring) < 3:
            rejected[key] = f"點數不足({len(ring)})"
            continue
        rings[key] = ring
        arcs[key] = tuple(ring_flags)
    return rings, rejected


def read_d12_children(path: Path) -> dict[ParcelKey, list[ParcelKey]]:
    """.D12 → 父地 -> 直屬地中地清單（每列一組父子關係）。"""

    children: dict[ParcelKey, list[ParcelKey]] = {}
    for row in read_dbf(path):
        parent = (
            int(row.get("O_SECTION") or 0),
            int(row.get("O_PARCEL") or 0),
            int(row.get("O_PARCEL_E") or 0),
        )
        child = (
            int(row.get("I_SECTION") or 0),
            int(row.get("I_PARCEL") or 0),
            int(row.get("I_PARCEL_E") or 0),
        )
        children.setdefault(parent, []).append(child)
    return children


def net_area(
    key: ParcelKey,
    rings: dict[ParcelKey, list[Point]],
    arcs: OrderedDict,
    children: dict[ParcelKey, list[ParcelKey]],
) -> float:
    """宗地淨面積＝外環面積 − 各**直屬**地中地外環面積（.D12）。

    BA0002 實測：760-73-9 外環 3748.758 m²，扣掉 23 筆地中地後 2280.976 m²，
    與 D11 `AREA_NEW` 的 2280.980 m² 相差 0.004 m²。
    """

    total = polygon_area(rings[key], arcs.get(key, ()))
    for child in children.get(key, ()):
        if child in rings:
            total -= polygon_area(rings[child], arcs.get(child, ()))
    return total


def read_d11_areas(path: Path) -> dict[ParcelKey, dict]:
    """.D11 → 新地號 key 的面積事實（公頃；×10000 得平方公尺）。"""

    areas: dict[ParcelKey, dict] = {}
    for row in read_dbf(path):
        key = (
            int(row.get("SECTION_N") or 0) or int(row.get("SECTION_O") or 0),
            int(row.get("PAR_N_M") or 0),
            int(row.get("PAR_N_C") or 0),
        )
        areas[key] = {
            "AREA_OLD": row.get("AREA_OLD"),
            "AREA_NEW": row.get("AREA_NEW"),
            "AREA_DIG": row.get("AREA_DIG"),
        }
    return areas


# ---------------------------------------------------------------------------
# 目錄層級：找檔、摘要、查詢
# ---------------------------------------------------------------------------


def find(root: Path, suffix: str) -> Path | None:
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.upper() == suffix.upper():
            return path
    return None


def format_key(key: ParcelKey) -> str:
    section, parcel, ext = key
    return f"{section}-{parcel}-{ext}" if ext else f"{section}-{parcel}"


def describe_exchange(path: Path) -> str:
    suffix = path.suffix.upper()
    if suffix == ".D25":
        return f"{len(read_d25(path))} 筆觀測記錄"
    lines = read_lines(path)
    if suffix == ".CNT":
        points, named, skipped = parse_cnt(lines)
        return f"{len(points)} 點（另 {len(named)} 個控制點名，略過 {skipped} 列）"
    if suffix == ".COA":
        points, skipped, source = parse_coa(lines)
        return f"{len(points)} 點（{source}，略過 {skipped} 列）"
    if suffix == ".RCO":
        return f"{len(parse_rco(lines))} 參考點"
    if suffix in (".BNI", ".BNP"):
        parsed = parse_bni(lines) if suffix == ".BNI" else parse_bnp(lines)
        return (
            f"{len(parsed.sequences)} 宗地／{parsed.arc_points} 弧中點"
            f"（{parsed.source}，略過 {parsed.skipped} 列）"
        )
    if suffix == ".PTM":
        return f"{len(parse_ptm(lines))} 筆宗地屬性（面積單位：公頃）"
    if suffix == ".PAR":
        rows, source = parse_par(lines)
        return f"{len(rows)} 筆宗地屬性（{source}，面積單位：平方公尺）"
    if suffix == ".INN":
        return f"{len(parse_inn(lines))} 筆新舊地號對照"
    if suffix == ".CTL":
        return f"{len(parse_ctl(lines))} 個圖根點"
    if suffix == ".MAC":
        blocks = parse_mac(lines)
        kinds = "／".join(sorted({block["kind"] for block in blocks})) or "—"
        return f"{len(blocks)} 個計算區塊（{kinds}）"
    return f"{path.stat().st_size} bytes"


def summarize(root: Path) -> int:
    print(f"段目錄：{root}")
    files = sorted(path for path in root.iterdir() if path.is_file())
    dbf_files = [path for path in files if is_dbf(path)]
    print(f"檔案 {len(files)} 個，其中 dBASE {len(dbf_files)} 個")
    for path in dbf_files:
        info = read_dbf_info(path)
        flag = "" if info.size_check(path.stat().st_size) else "  ⚠ 大小與檔頭不符"
        print(
            f"  {path.name:<16} {info.record_count:>7} 筆 × {info.record_length:>3} bytes"
            f"  {len(info.fields):>2} 欄{flag}"
        )
    for suffix, label in (
        (".D25", "測量資料記錄"),
        (".PTM", "重測宗地屬性"),
        (".BNI", "重測地號界址"),
        (".CNT", "重測界址坐標"),
        (".INN", "新舊地號對照"),
        (".PAR", "複丈宗地屬性"),
        (".BNP", "複丈地號界址"),
        (".COA", "複丈界址坐標"),
        (".RCO", "複丈參考坐標"),
        (".CTL", "圖根點坐標"),
        (".MAC", "測量文字檔"),
    ):
        path = find(root, suffix)
        if path is None:
            continue
        print(f"  {path.name:<16} {describe_exchange(path)}   ({label})")
    return 0


def verify_areas(root: Path, limit: int) -> int:
    """D13+D14 重建環面積 vs D11 AREA_NEW；差 > 2 m² 視為不可信。"""

    d13, d14, d11 = find(root, ".D13"), find(root, ".D14"), find(root, ".D11")
    d12 = find(root, ".D12")
    if d13 is None or d14 is None:
        print("此目錄沒有 .D13/.D14，無法重建宗地。")
        return 1
    sequences, arcs = read_d13_sequences(d13)
    confirmed, every = read_d14_points(d14)
    rings, rejected = build_rings(sequences, arcs, confirmed)
    children = read_d12_children(d12) if d12 else {}
    areas = read_d11_areas(d11) if d11 else {}
    print(f".D14 確定點 {len(confirmed)} / 全部點位 {len(every)}")
    print(f".D13 宗地 {len(sequences)}，成環 {len(rings)}，未成環 {len(rejected)}")
    if children:
        print(f".D12 父地 {len(children)} 筆（面積已扣除其地中地）")
    if not areas:
        return 0
    matched = failed = 0
    worst: list[tuple[float, ParcelKey, float, float]] = []
    for key in rings:
        recorded = areas.get(key, {}).get("AREA_NEW")
        if recorded is None:
            continue
        computed = net_area(key, rings, arcs, children)
        difference = abs(computed - recorded * 10000.0)
        worst.append((difference, key, computed, recorded * 10000.0))
        if difference <= 2.0:
            matched += 1
        else:
            failed += 1
    total = matched + failed
    if total:
        print(f"與 D11 AREA_NEW 比對：{matched}/{total} 在 2 m² 內（{matched / total:.2%}）")
    for difference, key, computed, recorded in sorted(worst, reverse=True)[:limit]:
        print(
            f"  {format_key(key):<14} 重建 {computed:12.3f} m²  D11 {recorded:12.3f} m²"
            f"  差 {difference:9.3f}"
        )
    return 0


def verify_exchange(root: Path, limit: int) -> int:
    """交換檔自我驗證：坐標＋點號序列重建環，再與屬性檔的面積比對。

    重測組 .CNT+.BNI+.PTM 以**原地號**對接（面積為公頃）；
    複丈整合版 .COA+.BNP+.PAR 以**新地號**對接（面積為平方公尺）。
    """

    cnt, bni, ptm = find(root, ".CNT"), find(root, ".BNI"), find(root, ".PTM")
    coa, bnp, par = find(root, ".COA"), find(root, ".BNP"), find(root, ".PAR")
    if cnt and bni:
        points = {
            number: coordinate
            for (number, ref), coordinate in parse_cnt(read_lines(cnt))[0].items()
            if ref == 0
        }
        parsed = parse_bni(read_lines(bni))
        areas = (
            {
                (row["SECTION_O"], row["PAR_O_M"], row["PAR_O_C"]): (
                    row["AREA_OLD_HA"] or 0.0
                )
                * 10000.0
                for row in parse_ptm(read_lines(ptm))
            }
            if ptm
            else {}
        )
        note = (
            ".PTM 是**原登記面積**；若 .CNT/.BNI 其實是現況匯出成果，兩者本來就會有差。"
        )
        label = f"{cnt.name} + {bni.name}" + (f" + {ptm.name}（原地號／公頃）" if ptm else "")
    elif coa and bnp:
        points = {
            number: coordinate
            for (number, _ref), coordinate in parse_coa(read_lines(coa))[0].items()
        }
        parsed = parse_bnp(read_lines(bnp))
        areas = (
            {
                (row["PAR_N_M"], row["PAR_N_C"]): row["AREA_NEW_M2"] or 0.0
                for row in parse_par(read_lines(par))[0]
            }
            if par
            else {}
        )
        note = "整合版一律以**新地號**對接；取 .PAR 的原地號欄會完全接不起來。"
        label = f"{coa.name} + {bnp.name}" + (f" + {par.name}（新地號／平方公尺）" if par else "")
    else:
        print("此目錄沒有成組的 .CNT+.BNI 或 .COA+.BNP。")
        return 1

    arcs = OrderedDict(parsed.arc_midpoints)
    rings, rejected = build_rings(parsed.sequences, arcs, points)
    print(f"{label}（{parsed.source}）")
    print(f"坐標 {len(points)} 點，宗地 {len(parsed.sequences)}，成環 {len(rings)}，未成環 {len(rejected)}")
    if not areas:
        return 0
    print(f"註：{note}")
    key_length = len(next(iter(areas)))  # 原地號組帶段號，整合版只有母/子
    matched = total = 0
    worst: list[tuple[float, ParcelKey, float, float]] = []
    for key, ring in rings.items():
        recorded = areas.get(key if key_length == 3 else (key[1], key[2]))
        if recorded is None:
            continue
        computed = polygon_area(ring, arcs.get(key, ()))
        difference = abs(computed - recorded)
        total += 1
        matched += difference <= max(2.0, recorded * 0.001)
        worst.append((difference, key, computed, recorded))
    if total:
        print(f"面積比對：{matched}/{total} 在 2 m² 或 0.1% 內（{matched / total:.2%}）")
    for difference, key, computed, recorded in sorted(worst, reverse=True)[:limit]:
        print(
            f"  {format_key(key):<14} 重建 {computed:12.3f} m²  登記 {recorded:12.3f} m²"
            f"  差 {difference:9.3f}"
        )
    return 0


def show_parcel(root: Path, text: str) -> int:
    d13, d14 = find(root, ".D13"), find(root, ".D14")
    if d13 is None or d14 is None:
        print("此目錄沒有 .D13/.D14。")
        return 1
    parts = [int(part) for part in text.replace("_", "-").split("-")]
    while len(parts) < 3:
        parts.append(0)
    key = (parts[0], parts[1], parts[2])
    sequences, arcs = read_d13_sequences(d13)
    confirmed, _ = read_d14_points(d14)
    numbers = sequences.get(key)
    if numbers is None:
        print(f"找不到宗地 {format_key(key)}")
        return 1
    print(f"宗地 {format_key(key)}：{len(numbers)} 個界址點")
    flags = arcs.get(key, ())
    for index, number in enumerate(numbers):
        coordinate = confirmed.get(number)
        mark = " (弧中點)" if index < len(flags) and flags[index] else ""
        if coordinate is None:
            print(f"  {number:>6}  —（D14 無確定點坐標，重建時排除）{mark}")
        else:
            print(f"  {number:>6}  X={coordinate[0]:.3f}  Y={coordinate[1]:.3f}{mark}")
    rings, rejected = build_rings(sequences, arcs, confirmed)
    if key not in rings:
        print(f"無法成環：{rejected.get(key)}")
        return 0
    d12 = find(root, ".D12")
    children = read_d12_children(d12) if d12 else {}
    outer = polygon_area(rings[key], arcs.get(key, ()))
    print(f"外環面積（含真弧）＝ {outer:.3f} m²")
    inner = [child for child in children.get(key, ()) if child in rings]
    if inner:
        print(f"扣除 {len(inner)} 筆地中地後淨面積＝ {net_area(key, rings, arcs, children):.3f} m²")
    return 0


def show_point(root: Path, number: int) -> int:
    d14 = find(root, ".D14")
    if d14 is None:
        print("此目錄沒有 .D14。")
        return 1
    found = False
    for row in read_dbf(d14):
        if int(row.get("COT_NUMBER") or 0) != number:
            continue
        found = True
        ref = int(row.get("COT_REF") or 0)
        kind = "確定點" if ref == 0 else f"參考點 .{ref}"
        print(
            f"{number}.{ref:<3} {kind:<10}"
            f" X={row.get('COT_X')}  Y={row.get('COT_Y')}"
            f"  來源={row.get('COT_SOURCE')}  樁={row.get('COT_MATTER')}"
            f"  註記={row.get('COT_REMARK')!r}"
        )
    if not found:
        print(f"D14 沒有點號 {number}")
        return 1
    return 0


def dump(path: Path, limit: int) -> int:
    if is_dbf(path):
        info = read_dbf_info(path)
        ok = "✓" if info.size_check(path.stat().st_size) else "⚠ 大小與檔頭不符"
        print(f"{path.name}: dBASE III  {info.record_count} 筆 × {info.record_length} bytes  {ok}")
        print(
            "欄位："
            + ", ".join(
                f"{field.name}({field.type}{field.length}"
                + (f".{field.decimals})" if field.decimals else ")")
                for field in info.fields
            )
        )
        for index, row in enumerate(read_dbf(path)):
            if index >= limit:
                break
            print(f"  {row}")
        return 0
    if path.suffix.upper() == ".D25":
        for index, row in enumerate(read_d25(path)):
            if index >= limit:
                break
            print(f"  {row}")
        return 0
    print(f"{path.name}: {describe_exchange(path)}")
    for index, line in enumerate(read_lines(path)):
        if index >= limit:
            break
        print(f"  {line!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="重測原始檔讀取器（唯讀）")
    parser.add_argument("target", type=Path, help="段目錄或單一檔案")
    parser.add_argument("--parcel", help="顯示一筆宗地的界址點與面積，如 755-365-2")
    parser.add_argument("--point", type=int, help="顯示一個 D14 點號的全部列")
    parser.add_argument("--verify-areas", action="store_true", help="D13+D14 對 D11 面積驗證")
    parser.add_argument(
        "--verify-exchange",
        action="store_true",
        help="交換檔（CNT+BNI+PTM 或 COA+BNP+PAR）自我驗證",
    )
    parser.add_argument("--dump", action="store_true", help="傾印單一檔案前幾筆")
    parser.add_argument("--limit", type=int, default=10, help="輸出筆數上限（預設 10）")
    args = parser.parse_args(argv)

    target: Path = args.target
    if not target.exists():
        print(f"找不到：{target}", file=sys.stderr)
        return 2
    if target.is_file():
        return dump(target, args.limit)
    if args.parcel:
        return show_parcel(target, args.parcel)
    if args.point is not None:
        return show_point(target, args.point)
    if args.verify_areas:
        return verify_areas(target, args.limit)
    if args.verify_exchange:
        return verify_exchange(target, args.limit)
    return summarize(target)


if __name__ == "__main__":
    raise SystemExit(main())
