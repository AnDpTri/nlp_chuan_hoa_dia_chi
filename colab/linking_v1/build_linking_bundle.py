"""Đóng gói Bundle Colab tự thân cho thí nghiệm Liên kết thực thể (Neural Linking v1).

Tạo ra file:
- `colab/dist/nlp_linking_bundle_v1.zip`
- `BUNDLE_MANIFEST.json` chứa mã hash SHA-256 và kích thước cho từng file.
- Tuyệt đối không chứa tập test cuối, không chứa virtualenv, không chứa file tạm.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parents[2]


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_bundle(output_zip: Path, staging_dir: Path) -> Dict[str, any]:
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    copied_files: List[Path] = []

    # 1. Mã nguồn src/ bao gồm src/lien_ket_v1/
    src_dir = ROOT_DIR / "src"
    for p in src_dir.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(ROOT_DIR)
        dest = staging_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        copied_files.append(dest)

    # 2. Scripts colab/linking_v1/
    colab_linking_dir = ROOT_DIR / "colab/linking_v1"
    for p in colab_linking_dir.glob("*"):
        if p.is_file() and not p.name.endswith(".zip") and p.name != "BUNDLE_MANIFEST.json":
            rel = p.relative_to(ROOT_DIR)
            dest = staging_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            copied_files.append(dest)

    # 3. Tests được chọn lọc (không bao gồm test liên quan đến data/test)
    test_files = [
        "test_lien_ket_v1.py",
        "test_pipeline.py",
        "test_pipeline_v3.py",
        "test_danh_gia.py",
        "test_char.py",
        "test_crf.py",
    ]
    for tf in test_files:
        p = ROOT_DIR / "tests" / tf
        if p.exists():
            rel = p.relative_to(ROOT_DIR)
            dest = staging_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            copied_files.append(dest)

    # Đảm bảo tests/__init__.py tồn tại
    test_init = staging_dir / "tests/__init__.py"
    test_init.parent.mkdir(parents=True, exist_ok=True)
    test_init.write_text("# tests\n", encoding="utf-8")
    copied_files.append(test_init)

    # 4. Danh mục data/clean/
    clean_dir = ROOT_DIR / "data/clean"
    for p in clean_dir.glob("*"):
        if p.is_file() and p.suffix in (".json", ".csv", ".md"):
            rel = p.relative_to(ROOT_DIR)
            dest = staging_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            copied_files.append(dest)

    # 5. Dữ liệu huấn luyện & dev snapshots
    train_data = ROOT_DIR / "data/train_dev/duyet_v2_01/train_cnn_ket_hop.jsonl"
    if train_data.exists():
        rel = train_data.relative_to(ROOT_DIR)
        dest = staging_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(train_data, dest)
        copied_files.append(dest)

    snapshot_dev = ROOT_DIR / "mo_hinh/thu_nghiem/char_v1_01/snapshot"
    if snapshot_dev.exists():
        for p in snapshot_dev.glob("*.csv"):
            rel = p.relative_to(ROOT_DIR)
            dest = staging_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            copied_files.append(dest)
        # Tạo alias dev_goc.csv trỏ tới dev.csv để tương thích cả 2 tên gọi
        dev_file = staging_dir / "mo_hinh/thu_nghiem/char_v1_01/snapshot/dev.csv"
        dev_goc_file = staging_dir / "mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_goc.csv"
        if dev_file.exists() and not dev_goc_file.exists():
            shutil.copy2(dev_file, dev_goc_file)
            copied_files.append(dev_goc_file)

    # 6. Tạo Manifest SHA-256
    manifest_entries = {}
    total_bytes = 0
    for p in staging_dir.rglob("*"):
        if p.is_file():
            rel_str = str(p.relative_to(staging_dir)).replace("\\", "/")
            fsize = p.stat().st_size
            fhash = compute_sha256(p)
            manifest_entries[rel_str] = {
                "size_bytes": fsize,
                "sha256": fhash,
            }
            total_bytes += fsize

    manifest = {
        "bundle_name": "nlp_linking_bundle_v1",
        "description": "Gói Colab trọn gói cho thí nghiệm Liên kết thực thể (Neural Linking v1)",
        "total_files": len(manifest_entries),
        "total_size_bytes": total_bytes,
        "files": manifest_entries,
    }

    manifest_path = staging_dir / "BUNDLE_MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 7. Đóng gói ZIP
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in staging_dir.rglob("*"):
            if p.is_file():
                arcname = str(p.relative_to(staging_dir)).replace("\\", "/")
                z.write(p, arcname)

    # 8. Kiểm tra tính toàn vẹn của file ZIP
    with zipfile.ZipFile(output_zip, "r") as z:
        corrupted = z.testzip()
        if corrupted is not None:
            raise ValueError(f"File ZIP bị lỗi tại: {corrupted}")
        # Kiểm tra checksum của các file trong zip
        for rel_name, meta in manifest_entries.items():
            content = z.read(rel_name)
            calc_hash = hashlib.sha256(content).hexdigest()
            if calc_hash != meta["sha256"]:
                raise ValueError(f"Checksum mismatch cho file {rel_name} trong ZIP!")

    zip_size = output_zip.stat().st_size
    zip_sha256 = compute_sha256(output_zip)

    summary = {
        "output_zip": str(output_zip),
        "zip_size_bytes": zip_size,
        "zip_size_mb": round(zip_size / (1024 * 1024), 2),
        "zip_sha256": zip_sha256,
        "total_files": len(manifest_entries),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Đóng gói nlp_linking_bundle_v1.zip")
    parser.add_argument(
        "--output_zip",
        type=str,
        default=str(ROOT_DIR / "colab/dist/nlp_linking_bundle_v1.zip"),
    )
    parser.add_argument(
        "--staging_dir",
        type=str,
        default=str(ROOT_DIR / "colab/dist/staging_linking_bundle"),
    )
    args = parser.parse_args()

    build_bundle(Path(args.output_zip), Path(args.staging_dir))


if __name__ == "__main__":
    main()
