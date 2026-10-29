"""Xuất checkpoint CPU dùng được và báo cáo; bỏ optimizer/resume và HF cache."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def export(run_dir, output):
    required = ['training.json', 'run_config.json', 'model/model.safetensors', 'model/model_config.json',
                'model/tokenizer.json', 'model/special_tokens_map.json']
    for name in required:
        if not (run_dir / name).is_file():
            raise FileNotFoundError(name)
    training = json.loads((run_dir / 'training.json').read_text(encoding='utf-8'))
    if not training['training_complete']:
        raise ValueError('Chưa train xong; giữ checkpoint trên Drive để resume trước')
    files = [p for p in run_dir.rglob('*') if p.is_file() and p.name not in ('resume.pt', 'resume.tmp')]
    if output.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError('Đặt ZIP ngoài run-dir để không tự đóng gói chính nó')
    if output.exists():
        raise FileExistsError('ZIP đã tồn tại; không ghi đè')
    manifest = {str(p.relative_to(run_dir)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for p in files:
            z.write(p, run_dir.name + '/' + str(p.relative_to(run_dir)).replace('\\', '/'))
        z.writestr(run_dir.name + '/SHA256_EXPORT.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output) as z:
        for name, expected in manifest.items():
            if hashlib.sha256(z.read(run_dir.name + '/' + name)).hexdigest() != expected:
                raise RuntimeError('ZIP khác checksum: ' + name)
    print(json.dumps({'zip': str(output), 'files': len(files), 'mib': output.stat().st_size / 2**20,
                      'optimizer_excluded': True}, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    export(args.run_dir, args.output)


if __name__ == '__main__':
    main()
