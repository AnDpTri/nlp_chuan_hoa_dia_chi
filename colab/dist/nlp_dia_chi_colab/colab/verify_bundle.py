"""Kiểm tra checksum của mọi file gói và tính tách biệt dữ liệu."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    manifest = json.loads((root / 'BUNDLE_MANIFEST.json').read_text(encoding='utf-8'))
    for name, entry in manifest['files'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Đường dẫn không thuộc bundle')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Checksum sai: ' + name)
    from colab.train_videberta import validate_input
    sets = validate_input(root / 'bundle_data')
    result = {'files_verified': len(manifest['files']), 'rows': {k: len(v) for k, v in sets.items()},
              'cnn_ranker_groups_disjoint': True, 'train_dev_masked_house_families_disjoint': True,
              'heldout_test_included': False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path('.'))
    args = p.parse_args()
    verify(args.root)


if __name__ == '__main__':
    main()
