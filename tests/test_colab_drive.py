"""Kiểm tra chuyển gói qua filesystem Drive bằng thư mục tạm, không dùng Drive thật."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from colab import prepare_drive as pd
from colab.build_bundle import notebook


class ColabDriveTests(unittest.TestCase):
    def test_drive_notebook_bo_upload_download_va_compile(self):
        original = notebook()
        changed = pd.drive_notebook(original, 'abc123')
        source = '\n'.join(''.join(c['source']) for c in changed['cells'] if c['cell_type'] == 'code')
        self.assertNotIn('files.upload()', source)
        self.assertNotIn('files.download(', source)
        self.assertIn('drive.mount', source)
        self.assertIn('abc123', source)
        self.assertIn('EXPORT_DIR = DRIVE_ROOT', source)
        self.assertEqual(original['cells'][12]['source'], changed['cells'][12]['source'])
        for cell in changed['cells']:
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), '<test>', 'exec')

    def test_copy_va_cap_nhat_tai_cho_giu_cau_hinh_va_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root, drive = Path(d) / 'project', Path(d) / 'Drive'
            (root / 'colab/dist').mkdir(parents=True)
            archive = root / 'colab/dist/nlp_dia_chi_colab_v1.zip'
            archive.write_bytes(b'fixture-zip')
            (drive / 'Colab Notebooks').mkdir(parents=True)
            existing = drive / 'Colab Notebooks/ViDeBERTa_Colab.ipynb'
            nb = notebook()
            nb['metadata']['preserve_this'] = 'metadata'
            nb['cells'][10]['source'] = ['RUN_ID = "custom_run"\n']
            original = json.dumps(nb).encode()
            existing.write_bytes(original)
            with patch.object(pd, 'ROOT', root):
                r = pd.prepare(drive)
            updated = json.loads(existing.read_text(encoding='utf-8'))
            self.assertEqual(updated['metadata']['preserve_this'], 'metadata')
            self.assertEqual(updated['cells'][10]['source'], nb['cells'][10]['source'])
            self.assertTrue(r['existing_colab_notebook_updated_in_place'])
            self.assertFalse(r['training_started'])
            self.assertEqual((drive / 'nlp_chuan_hoa_dia_chi' / archive.name).read_bytes(), b'fixture-zip')
            backup = list((root / 'colab/kiem_tra/drive_backup').glob('*.ipynb'))
            self.assertEqual(backup[0].read_bytes(), original)

    def test_khong_ghi_de_zip_khac_noi_dung(self):
        with tempfile.TemporaryDirectory() as d:
            root, drive = Path(d) / 'project', Path(d) / 'Drive'
            (root / 'colab/dist').mkdir(parents=True)
            (root / 'colab/dist/nlp_dia_chi_colab_v1.zip').write_bytes(b'new')
            target = drive / 'nlp_chuan_hoa_dia_chi'
            target.mkdir(parents=True)
            (target / 'nlp_dia_chi_colab_v1.zip').write_bytes(b'existing')
            with patch.object(pd, 'ROOT', root), self.assertRaisesRegex(FileExistsError, 'khác nội dung'):
                pd.prepare(drive)
            self.assertEqual((target / 'nlp_dia_chi_colab_v1.zip').read_bytes(), b'existing')


if __name__ == '__main__':
    unittest.main()
