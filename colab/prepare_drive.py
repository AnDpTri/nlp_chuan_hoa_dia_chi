"""Chuẩn bị notebook Drive-first và chuyển gói bằng Drive for desktop.

Không lấy cookie/token, không dùng UI, không thay đổi quyền chia sẻ.
Notebook đã tồn tại được ghi nội dung tại chỗ để giữ file/ID Colab.
"""

import argparse
import copy
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .build_bundle import notebook

ROOT = Path(__file__).resolve().parents[1]


def drive_notebook(base, bundle_hash, bundle_name='nlp_dia_chi_colab_v1.zip'):
    result = copy.deepcopy(base)
    by_id = {c['id']: c for c in result['cells']}
    replacements = {
        'cell-00': '# Fine-tune ViDeBERTa-xsmall — đọc gói và lưu kết quả trên Drive\n\n'
                   'Gói ZIP đã được đặt trong `My Drive/nlp_chuan_hoa_dia_chi/`. '
                   'Chọn GPU rồi chạy từng mục; không dùng widget upload file. '
                   'Mount Drive lần đầu có thể cần xác nhận tài khoản.\n\n'
                   '**Cấu hình mặc định:** 5 epoch, 4.841 mẫu train nhận diện và 1.169 mẫu riêng cho ranker. '
                   'Không có nhãn test cuối. Checkpoint và báo cáo được lưu trên Drive. '
                   'Train GPU dự trù 10–30 phút, ETA thực được in sau 10 batch.',
        'cell-03': '## 2. Đọc gói từ Drive\n'
                   'Kết nối Drive rồi giải nén gói đã có vào `/content` để xử lý nhanh. '
                   'Kiểm tra SHA-256 trước khi dùng. Không cần upload lại ZIP khi Colab bị ngắt.',
        'cell-04': 'from google.colab import drive\n'
                   'from pathlib import Path\n'
                   'import zipfile, os, sys, hashlib\n\n'
                   'drive.mount("/content/drive")\n'
                   'DRIVE_ROOT = Path("/content/drive/MyDrive/nlp_chuan_hoa_dia_chi")\n'
                   f'ZIP_PATH = DRIVE_ROOT / {json.dumps(bundle_name)}\n'
                   'assert ZIP_PATH.is_file(), f"Chưa thấy ZIP đồng bộ lên Drive: {ZIP_PATH}"\n'
                   f'assert hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest() == "{bundle_hash}", "ZIP khác bản đã kiểm tra"\n'
                   'PROJECT = Path("/content/nlp_dia_chi_colab")\n'
                   'with zipfile.ZipFile(ZIP_PATH) as z:\n'
                   '    for name in z.namelist():\n'
                   '        assert (Path("/content") / name).resolve().is_relative_to(PROJECT), name\n'
                   '    z.extractall("/content")\n'
                   'os.chdir(PROJECT)\n'
                   'sys.path.insert(0, str(PROJECT))\n'
                   'print("Đã đọc gói từ Drive:", ZIP_PATH)\n',
        'cell-17': '## 9. Xuất kết quả thẳng về Drive\n'
                   'ZIP kết quả được lưu trong `My Drive/nlp_chuan_hoa_dia_chi/ket_qua/`. '
                   'Drive for desktop sẽ đồng bộ về máy; không cần widget download. '
                   'Optimizer/resume lớn vẫn nằm trong thư mục run để tiếp tục khi bị ngắt.',
        'cell-18': 'from datetime import datetime\n'
                   'EXPORT_DIR = DRIVE_ROOT / "ket_qua"\n'
                   'EXPORT_DIR.mkdir(parents=True, exist_ok=True)\n'
                   'RESULT_ZIP = EXPORT_DIR / (RUN_ID + "_ket_qua_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip")\n'
                   'from colab.notebook_runner import run_visible\n'
                   'run_visible([sys.executable, "-m", "colab.export_results", "--run-dir", str(RUN_DIR), '
                   '"--output", str(RESULT_ZIP)], log_path=DRIVE_ROOT / "logs/cell-18.log")\n'
                   'print("Đã lưu kết quả trên Drive:", RESULT_ZIP)\n',
    }
    for cell_id, source in replacements.items():
        if cell_id not in by_id:
            raise ValueError('Notebook không đúng cấu trúc đã tạo: ' + cell_id)
        cell = by_id[cell_id]
        cell['source'] = source.splitlines(keepends=True)
        if cell['cell_type'] == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
    for cell in result['cells']:
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), '<drive-notebook>', 'exec')
    return result


def prepare(drive_root, update_existing=True, archive=None, restore_clean=False):
    drive_root = drive_root.resolve()
    if not drive_root.is_dir():
        raise FileNotFoundError('Drive chưa được mount: ' + str(drive_root))
    archive = Path(archive) if archive else ROOT / 'colab/dist/nlp_dia_chi_colab_v1.zip'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    bundle_hash = digest(archive)
    target = drive_root / 'nlp_chuan_hoa_dia_chi'
    target.mkdir(exist_ok=True)
    backup = ROOT / 'colab/kiem_tra/drive_backup'
    backup.mkdir(parents=True, exist_ok=True)
    existing = drive_root / 'Colab Notebooks/ViDeBERTa_Colab.ipynb'
    destination = target / archive.name
    if destination.exists() and digest(destination) != bundle_hash:
        raise FileExistsError('Drive có ZIP cùng tên khác nội dung; không ghi đè')
    if not destination.exists():
        shutil.copy2(archive, destination)
    if digest(destination) != bundle_hash:
        raise RuntimeError('ZIP trên ổ Drive không đúng checksum')
    clean = drive_notebook(notebook(archive.name), bundle_hash, archive.name)
    payload = (json.dumps(clean, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    local = ROOT / 'colab/ViDeBERTa_Drive.ipynb'
    local.write_bytes(payload)
    drive_copy = target / local.name
    drive_copy.write_bytes(payload)
    changed_existing = False
    if update_existing and existing.exists():
        original = existing.read_bytes()
        original_hash = hashlib.sha256(original).hexdigest()
        saved = backup / (original_hash[:16] + '_ViDeBERTa_Colab.ipynb')
        if not saved.exists():
            saved.write_bytes(original)
        # Chỉ thay các ô đọc/xuất gói; giữ các ô train, cấu hình và metadata khác.
        original_nb = json.loads(original)
        if restore_clean:
            updated = copy.deepcopy(clean)
            updated['metadata'] = copy.deepcopy(original_nb.get('metadata', clean['metadata']))
            updated['metadata'].pop('widgets', None)
            for c in original_nb['cells']:
                if c.get('id', c.get('metadata', {}).get('id')) == 'cell-10':
                    updated['cells'][10]['source'] = copy.deepcopy(c['source'])
            for c in updated['cells']:
                if c['cell_type'] == 'code':
                    compile(''.join(c['source']), '<restored-notebook>', 'exec')
        else:
            updated = drive_notebook(original_nb, bundle_hash, archive.name)
        if existing.read_bytes() != original:
            raise RuntimeError('Notebook đã thay đổi trong lúc chuẩn bị; chưa ghi đè')
        # Ghi tại chỗ, không rename/replace file đang được Drive quản lý.
        existing.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        reread = json.loads(existing.read_text(encoding='utf-8'))
        assert ''.join(reread['cells'][4]['source']) == ''.join(updated['cells'][4]['source'])
        changed_existing = True
    report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'method': 'Google Drive for desktop qua filesystem, không dùng UI/cookie/token',
              'drive_folder': str(target), 'zip': str(destination), 'zip_sha256': bundle_hash,
              'zip_verified_on_drive_filesystem': True,
              'notebook_local': str(local), 'notebook_drive': str(drive_copy),
              'notebook_copy_sha256_verified': digest(local) == digest(drive_copy),
              'existing_colab_notebook_updated_in_place': changed_existing,
              'restored_clean_notebook': restore_clean and changed_existing,
              'existing_colab_path': str(existing) if changed_existing else None,
              'file_sharing_changed': False, 'training_started': False,
              'cloud_sync_note': 'Đã xác minh file trên ổ Drive for desktop; đồng bộ server do ứng dụng Drive thực hiện.'}
    (ROOT / 'colab/kiem_tra/DRIVE_TRANSFER.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--drive-root', type=Path, default=Path('G:/My Drive'))
    p.add_argument('--no-update-existing', action='store_true')
    p.add_argument('--bundle', type=Path)
    p.add_argument('--restore-clean', action='store_true', help='Backup rồi khôi phục các ô sạch, bỏ ô vá phát sinh')
    args = p.parse_args()
    prepare(args.drive_root, not args.no_update_existing, args.bundle, args.restore_clean)


if __name__ == '__main__':
    main()
