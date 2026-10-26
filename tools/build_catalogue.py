"""Tạo lớp loại tỉnh mốc 2025 từ workbook raw, giữ nguyên clean/test."""

from pathlib import Path
import csv
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def build():
    source = ROOT / "data/raw/goc/conversion-table.xlsx"
    provinces = {}
    ward_codes = {}
    with zipfile.ZipFile(source) as z:
        strings = [
            "".join(n.text or "" for n in x.iter("{" + NS["m"] + "}t"))
            for x in ET.fromstring(z.read("xl/sharedStrings.xml"))
        ]
        for row in ET.fromstring(z.read("xl/worksheets/sheet2.xml")).findall(
            "m:sheetData/m:row", NS
        ):
            cells = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                value = v.text if v is not None and v.text else ""
                cells[re.sub(r"\d", "", c.attrib["r"])] = unicodedata.normalize(
                    "NFC",
                    (
                        strings[int(value)]
                        if c.attrib.get("t") == "s" and value
                        else value
                    ),
                )
            p = re.fullmatch(
                r"(Thành phố|Tỉnh)\s+(.+?)\s+\((\d{2})\)", cells.get("A", "").strip()
            )
            code = cells.get("C", "").strip()
            if p and code.isdigit():
                item = {"ma_tinh": p[3], "ten_tinh": p[2], "loai_tinh": p[1]}
                if p[3] in provinces and provinces[p[3]] != item:
                    raise ValueError("Nguồn mâu thuẫn loại tỉnh")
                provinces[p[3]] = item
                ward_codes[code.zfill(5)] = p[3]
    with (ROOT / "data/clean/moi_tinh.csv").open(encoding="utf-8-sig", newline="") as f:
        clean = list(csv.DictReader(f))
    with (ROOT / "data/clean/moi_tinh_xa.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        wards = list(csv.DictReader(f))
    if set(provinces) != {r["ma_tinh"] for r in clean} or len(provinces) != 34:
        raise ValueError("Không đủ 34 tỉnh")
    if ward_codes != {r["ma_xa"]: r["ma_tinh"] for r in wards} or len(wards) != 3321:
        raise ValueError("Khác mã hoặc quan hệ xã")
    out = ROOT / "data/runtime"
    out.mkdir(exist_ok=True)
    with (out / "loai_moc_2025.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["ma_tinh", "ten_tinh", "loai_tinh"], lineterminator="\n"
        )
        w.writeheader()
        w.writerows(provinces[k] for k in sorted(provinces))
    changes = [
        dict(
            ma_tinh=r["ma_tinh"],
            loai_clean=r["loai_tinh"],
            loai_runtime=provinces[r["ma_tinh"]]["loai_tinh"],
        )
        for r in clean
        if r["loai_tinh"] != provinces[r["ma_tinh"]]["loai_tinh"]
    ]
    (out / "catalogue_manifest.json").write_text(
        json.dumps(
            {
                "as_of": "2025-07-01",
                "source": "data/raw/goc/conversion-table.xlsx",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "province_count": 34,
                "ward_count": 3321,
                "type_overrides": changes,
                "policy": "Raw/clean/test không sửa; lớp runtime chỉ đổi loại tỉnh theo workbook đã có.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "Runtime catalogue built:",
        len(changes),
        "type corrections; raw/clean/test unchanged",
    )


if __name__ == "__main__":
    build()
