"""Hồi quy lỗi manifest Windows/Linux và log subprocess bị ẩn trong notebook."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.duong_dan import tu_manifest
from colab.notebook_runner import run_visible
from colab.build_bundle import notebook
from colab import prepare_drive as pd


class ColabPortableTests(unittest.TestCase):
    def test_key_manifest_windows_va_posix_tro_dung_cung_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'clean').mkdir()
            original = b'fixture-content'
            (root / 'clean/a.csv').write_bytes(original)
            for name in ('clean/a.csv', r'clean\a.csv'):
                p = tu_manifest(root, name)
                self.assertEqual(p.relative_to(root).parts, ('clean', 'a.csv'))
                self.assertEqual(hashlib.sha256(p.read_bytes()).digest(), hashlib.sha256(original).digest())

    def test_chan_duong_dan_vuot_root(self):
        for name in ('../a', r'..\a', '/tmp/a', r'C:\tmp\a', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                tu_manifest(Path.cwd(), name)

    def test_stdout_stderr_co_tren_notebook_va_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / 'logs/a.txt'
            capture = io.StringIO()
            with redirect_stdout(capture):
                result = run_visible([sys.executable, '-c', 'import sys; print("STDOUT", flush=True); print("STDERR", file=sys.stderr, flush=True)'], log_path=log)
            self.assertEqual(result.returncode, 0)
            for s in ('STDOUT', 'STDERR'):
                self.assertIn(s, capture.getvalue())
                self.assertIn(s, log.read_text(encoding='utf-8'))

    def test_loi_child_process_van_phai_chan(self):
        capture = io.StringIO()
        with redirect_stdout(capture), self.assertRaises(subprocess.CalledProcessError) as failure:
            run_visible([sys.executable, '-c', 'import sys; print("ROOT_ERROR", file=sys.stderr, flush=True); sys.exit(23)'])
        self.assertEqual(failure.exception.returncode, 23)
        self.assertIn('ROOT_ERROR', capture.getvalue())

    def test_notebook_log_tat_ca_cac_buoc_dai_va_giu_verify_chan(self):
        nb = notebook('nlp_dia_chi_colab_v2.zip')
        for index in (6, 8, 12, 14, 16, 18):
            source = ''.join(nb['cells'][index]['source'])
            self.assertIn('run_visible(', source)
            self.assertNotIn('subprocess.run(', source)
            compile(source, '<notebook>', 'exec')
        self.assertNotIn('except', ''.join(nb['cells'][8]['source']))

    def test_restore_clean_bo_o_va_va_backup_giu_cau_hinh(self):
        with tempfile.TemporaryDirectory() as d:
            root, drive = Path(d) / 'project', Path(d) / 'Drive'
            (root / 'colab/dist').mkdir(parents=True)
            archive = root / 'colab/dist/nlp_dia_chi_colab_v2.zip'
            archive.write_bytes(b'v2-fixture')
            (drive / 'Colab Notebooks').mkdir(parents=True)
            existing = drive / 'Colab Notebooks/ViDeBERTa_Colab.ipynb'
            nb = notebook()
            nb['cells'][10]['source'] = ['RUN_ID = "keep_my_run"\n']
            nb['cells'].insert(9, {'id': 'gemini_patch', 'cell_type': 'code', 'source': ['raise RuntimeError("do not run")'], 'metadata': {}, 'outputs': [], 'execution_count': None})
            original = json.dumps(nb).encode()
            existing.write_bytes(original)
            with patch.object(pd, 'ROOT', root), redirect_stdout(io.StringIO()):
                report = pd.prepare(drive, archive=archive, restore_clean=True)
            fixed = json.loads(existing.read_text(encoding='utf-8'))
            self.assertEqual(len(fixed['cells']), 19)
            self.assertEqual(fixed['cells'][10]['source'], ['RUN_ID = "keep_my_run"\n'])
            self.assertIn('nlp_dia_chi_colab_v2.zip', ''.join(fixed['cells'][4]['source']))
            self.assertIn('run_visible', ''.join(fixed['cells'][8]['source']))
            self.assertTrue(report['restored_clean_notebook'])
            self.assertEqual(next((root / 'colab/kiem_tra/drive_backup').glob('*.ipynb')).read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
