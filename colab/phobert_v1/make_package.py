"""Frozen Colab train bundle, fail-closed, copy to mounted Google Drive G:."""
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from check_data import TAGS, DATA_FILES, inspect, sha256

ROOT = Path(__file__).resolve().parents[2]
CODE = Path(__file__).resolve().parent
DEST = ROOT / "danh_gia/ket_qua/phobert_colab_package_v2_20261030"
NAME = "PhoBERT_Colab_v2_20261030"
BUNDLE = DEST / NAME
DRIVE = Path("G:/My Drive/PhoBERT_Address_Colab_20261030_v2")


def cell(source, md=False):
    result = {"cell_type": "markdown" if md else "code", "metadata": {},
              "source": source.splitlines(keepends=True)}
    if not md:
        result.update({"execution_count": None, "outputs": []})
    return result


def notebook():
    cells = [
        cell("# Huấn luyện PhoBERT-base-v2 cho địa chỉ Việt Nam\nChỉ sử dụng train và dev; không sử dụng test 400. Chạy từng ô và giám sát file status trong Drive.", True),
        cell("from google.colab import drive\ndrive.mount('/content/drive')\nfrom pathlib import Path\nD = Path('/content/drive/MyDrive/PhoBERT_Address_Colab_20261030_v2')\nARCHIVE = D / 'PhoBERT_Colab_v2_20261030.zip'\nassert ARCHIVE.is_file(), f'Archive not found: {ARCHIVE}'\nprint('DRIVE_PACKAGE:', ARCHIVE)\n"),
        cell("import zipfile\nwith zipfile.ZipFile(ARCHIVE) as z:\n    assert z.testzip() is None\n    assert all('test' not in Path(p).name.lower() for p in z.namelist() if p.endswith('.jsonl'))\n    z.extractall('/content')\nP = Path('/content/PhoBERT_Colab_v2_20261030')\nprint('UNPACKED:', P)\n"),
        cell("import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(P / 'requirements.txt')], check=True)\nprint('INSTALL_PASS')\n"),
        cell("subprocess.run([sys.executable, str(P / 'check_data.py'), '--data-dir', str(P / 'data'), '--manifest', str(P / 'package_manifest.json')], check=True)\n"),
        cell("import torch\nassert torch.cuda.is_available(), 'Please select Colab GPU runtime (T4 or better)'\nprint('GPU:', torch.cuda.get_device_name(0), 'CUDA:', torch.version.cuda)\n"),
        cell("## Smoke test v2\nKiểm tra **toàn bộ** train/dev bằng tokenizer chính thức rồi dùng 7 mẫu đầu + 1 mẫu có token OOV từng gây CUDA assert để thử GPU. Chỉ huấn luyện đầy đủ nếu smoke PASS.", True),
        cell("from datetime import datetime, timezone\ndef fresh_output(prefix):\n    path = D / 'runs' / (prefix + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))\n    assert not path.exists()\n    return path\nSMOKE = fresh_output('smoke')\ncmd = [sys.executable, str(P / 'train.py'), '--data-dir', str(P / 'data'), '--manifest', str(P / 'package_manifest.json'), '--out-dir', str(SMOKE), '--smoke', '--epochs', '1', '--batch-size', '4']\nsubprocess.run(cmd, check=True)\nassert (SMOKE / 'summary.json').is_file(), 'Smoke failed - STOP'\nprint('SMOKE_PASS:', SMOKE)\n"),
        cell("## Huấn luyện đầy đủ\nTheo dõi Google Drive/runs/<run-id>/status.json và history.json sau mỗi epoch.", True),
        cell("RUN = fresh_output('phobert_base_v2')\ncmd = [sys.executable, str(P / 'train.py'), '--data-dir', str(P / 'data'), '--manifest', str(P / 'package_manifest.json'), '--out-dir', str(RUN), '--epochs', '6', '--batch-size', '8', '--grad-accum', '2', '--seed', '20261030', '--lr', '2e-5', '--patience', '2']\nprint('LIVE_MONITOR:', RUN / 'status.json')\nsubprocess.run(cmd, check=True)\nassert (RUN / 'summary.json').is_file()\nprint('TRAINING_COMPLETE:', RUN)\n"),
        cell("import json\nprint(json.dumps(json.loads((RUN / 'summary.json').read_text()), indent=2, ensure_ascii=False))\nprint('BEST_MODEL:', RUN / 'best_model')\nprint('Note: token BIO metrics on weak labels, not end-to-end six-field accuracy.')\n"),
    ]
    book = {"cells": cells, "metadata": {
        "colab": {"name": "TRAIN_PhoBERT_Colab.ipynb"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5}
    (BUNDLE / "TRAIN_PhoBERT_Colab.ipynb").write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (CODE / "TRAIN_PhoBERT_Colab.ipynb").write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def main():
    assert not BUNDLE.exists(), "Bundle already exists, no overwrite"
    zpath = DEST / (NAME + ".zip")
    assert not zpath.exists(), "Zip already exists, no overwrite"
    BUNDLE.mkdir(parents=True)
    data = BUNDLE / "data"
    data.mkdir()
    source = ROOT / "mo_hinh/thu_nghiem/char_v2_01/data"
    for name in DATA_FILES:
        shutil.copy2(source / name, data / name)
    manifest = {
        "format": 1, "model": "vinai/phobert-base-v2",
        "source": "mo_hinh/thu_nghiem/char_v2_01/data",
        "scope": "TRAIN+DEV only, never test",
        "source_commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
        "tag_schema": TAGS, "sha256": {name: sha256(data / name) for name in DATA_FILES}}
    (BUNDLE / "package_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    checks = inspect(data, BUNDLE / "package_manifest.json")
    for name in ("train.py", "check_data.py", "requirements.txt", "README.md"):
        shutil.copy2(CODE / name, BUNDLE / name)
    notebook()
    (BUNDLE / "PREFLIGHT_LOCAL.json").write_text(json.dumps({"status": "PASS", "checks": checks}, indent=2), encoding="utf-8", newline="\n")
    with zipfile.ZipFile(zpath, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(BUNDLE.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(DEST).as_posix())
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None, "ZIP CRC error"
        assert len(z.namelist()) == 10, "Unexpected bundle file count"
        assert not any("dia_chi_test" in s.lower() or "/test" in s.lower() for s in z.namelist())
    assert DRIVE.parent.is_dir(), "Google Drive not mounted on G:"
    assert not DRIVE.exists(), "Drive output already exists"
    DRIVE.mkdir()
    shutil.copy2(zpath, DRIVE / zpath.name)
    for name in ("TRAIN_PhoBERT_Colab.ipynb", "README.md", "package_manifest.json"):
        shutil.copy2(BUNDLE / name, DRIVE / name)
    assert sha256(zpath) == sha256(DRIVE / zpath.name), "Drive checksum mismatch"
    summary = {"state": "DRIVE_COPY_HASH_VERIFIED", "drive": str(DRIVE),
               "archive_bytes": zpath.stat().st_size, "sha256": sha256(zpath),
               "source_commit": manifest["source_commit"], "counts": checks}
    (DEST / "DELIVERY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
