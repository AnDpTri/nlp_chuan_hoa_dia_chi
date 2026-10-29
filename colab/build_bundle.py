"""Tạo ZIP Colab bằng whitelist; không kèm test cuối, venv hoặc lịch sử chat."""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def notebook(bundle_name='nlp_dia_chi_colab_v1.zip'):
    cells = []
    def md(s):
        cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': s.splitlines(keepends=True)})
    def code(s):
        cells.append({'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': s.splitlines(keepends=True)})
    md('# Fine-tune ViDeBERTa-xsmall cho chuẩn hóa địa chỉ\n\n'
       'Chọn **Runtime → Change runtime type → GPU**, rồi chạy các ô theo thứ tự. '
       'Upload `nlp_dia_chi_colab_v1.zip` ở ô 2. Không cần GitHub hoặc Hugging Face token.\n\n'
       '**Mặc định:** 5 epoch trên 4.841 mẫu, 1.169 mẫu riêng cho ranker; dev gốc 1.136 và dev khó 464 câu. '
       'Không có tập test cuối trong gói. Dự trù train GPU 10–30 phút, ETA được in sau 10 batch; '
       'đây là ước lượng, chưa đo trên GPU Colab. Dùng Drive để giữ checkpoint khi runtime bị ngắt.')
    md('## 1. Kiểm tra GPU')
    code('import sys, subprocess, torch\n'
         'assert torch.cuda.is_available(), "Bật GPU ở Runtime → Change runtime type trước khi chạy tiếp"\n'
         'print("Torch:", torch.__version__, "GPU:", torch.cuda.get_device_name())\n'
         'subprocess.run(["nvidia-smi"], check=True)\n')
    md('## 2. Upload và giải nén gói dự án\nChỉ chọn ZIP đi kèm notebook này. Nếu chạy lại trong cùng runtime, thư mục đã giải nén sẽ được dùng lại và kiểm checksum ở ô 4.')
    code('from google.colab import files\nfrom pathlib import Path\nimport zipfile, os, json\n'
         'uploaded = files.upload()\n'
         'zip_names = [n for n in uploaded if n.endswith(".zip")]\n'
         'assert len(zip_names) == 1, "Chọn đúng một ZIP dự án"\n'
         'PROJECT = Path("/content/nlp_dia_chi_colab")\n'
         'if not PROJECT.exists():\n'
         '    with zipfile.ZipFile(zip_names[0]) as z:\n'
         '        for name in z.namelist():\n'
         '            assert (Path("/content") / name).resolve().is_relative_to(Path("/content/nlp_dia_chi_colab")), name\n'
         '        z.extractall("/content")\n'
         'os.chdir(PROJECT)\nsys.path.insert(0, str(PROJECT))\n'
         'del uploaded\nprint(PROJECT)\n')
    md('## 3. Cài thư viện\nGiữ nguyên PyTorch CUDA của Colab. Không chạy `requirements-neural.txt` vì đó là môi trường CPU cũ.')
    code('subprocess.run([sys.executable, "-m", "pip", "install", "-r", "colab/requirements.txt"], check=True)\n'
         'assert torch.cuda.is_available(), "CUDA phải còn hoạt động sau cài thư viện"\n')
    md('## 4. Kiểm tra gói và smoke test\nCác test dùng backbone tí hon để kiểm tra gradient, lưu/nạp, Unicode và pipeline; chưa phải fine-tune đầy đủ.')
    code('subprocess.run([sys.executable, "-m", "colab.verify_bundle", "--root", str(PROJECT)], check=True)\n'
         'subprocess.run([sys.executable, "-m", "unittest", "tests.test_videberta_colab", "tests.test_char", '
         '"tests.test_pipeline", "tests.test_pipeline_v3", "tests.test_crf", "tests.test_danh_gia"], check=True)\n')
    md('## 5. Nơi lưu và cấu hình\nDrive được khuyên dùng để giữ checkpoint. Nếu không dùng Drive, cần tải kết quả về trước khi Colab kết thúc. '
       'Giữ nguyên cấu hình khi resume. Muốn đổi batch/epoch thì đổi RUN_ID để tạo một lần thử mới. '
       'Nếu hết VRAM, dùng BATCH_SIZE=4 và GRAD_ACC=4 trong một run mới.')
    code('USE_DRIVE = True\nRUN_ID = "videberta_v1_01"\nEPOCHS = 5\nBATCH_SIZE = 8\nGRAD_ACC = 2\n'
         'if USE_DRIVE:\n'
         '    from google.colab import drive\n'
         '    drive.mount("/content/drive")\n'
         '    RUN_DIR = Path("/content/drive/MyDrive/nlp_chuan_hoa_dia_chi") / RUN_ID\n'
         'else:\n'
         '    RUN_DIR = Path("/content/runs") / RUN_ID\n'
         'print("Run:", RUN_DIR, "Resume:", RUN_DIR.exists())\n')
    md('## 6. Fine-tune GPU\nCheckpoint pretrained được tải trực tiếp từ commit đã chốt. '
       'Lưu model và resume sau mỗi epoch. Resume quay lại epoch hoàn chỉnh gần nhất; '
       'nếu chưa xong epoch nào thì bắt đầu lại epoch 1. Không dùng dev để chọn checkpoint.')
    code('cmd = [sys.executable, "-u", "-m", "colab.train_videberta", "--data-root", "bundle_data", '
         '"--run-dir", str(RUN_DIR), "--epochs", str(EPOCHS), "--batch-size", str(BATCH_SIZE), '
         '"--gradient-accumulation", str(GRAD_ACC)]\n'
         'if RUN_DIR.exists():\n    cmd.append("--resume")\n'
         'subprocess.run(cmd, check=True)\n'
         'print((RUN_DIR / "training.json").read_text())\n')
    md('## 7. Train ranker và đánh giá CPU\nRanker học trên phần train riêng; đo dev với luật v3, CRF cũ, ViDeBERTa dùng điểm tay và dùng ranker. '
       '**Độ trễ ở đây là CPU Colab**, không phải CPU laptop. Tỷ lệ khớp là với nhãn máy/tổng hợp, chưa phải gold. '
       'Muốn đo lại, đổi tên thư mục báo cáo để giữ lịch sử.')
    code('REPORT_DIR = RUN_DIR / "reports_cpu_colab_01"\n'
         'subprocess.run([sys.executable, "-u", "-m", "colab.evaluate_videberta", '
         '"--run-dir", str(RUN_DIR), "--output", str(REPORT_DIR)], check=True)\n'
         'print((REPORT_DIR / "BAO_CAO.md").read_text())\n')
    md('## 8. Thử một địa chỉ trên CPU')
    code('subprocess.run([sys.executable, "-m", "src", '
         '"Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội", '
         '"--videberta-model", str(RUN_DIR / "model"), "--ranker", str(RUN_DIR / "ranker.txt"), '
         '"--threads", "1"], check=True)\n')
    md('## 9. Xuất và tải kết quả\nZIP chứa model, tokenizer, ranker, dữ liệu snapshot, cấu hình và báo cáo. '
       'Optimizer/resume lớn được giữ trên Drive, không đưa vào ZIP tải về. '
       'Giải nén ZIP kết quả vào `D:\\nlp_chuan_hoa_dia_chi\\mo_hinh\\thu_nghiem\\`; '
       'xem lệnh chạy CPU trong hướng dẫn đi kèm gói ban đầu.')
    code('from datetime import datetime\n'
         'RESULT_ZIP = Path("/content") / (RUN_ID + "_ket_qua_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip")\n'
         'subprocess.run([sys.executable, "-m", "colab.export_results", "--run-dir", str(RUN_DIR), '
         '"--output", str(RESULT_ZIP)], check=True)\n'
         'files.download(str(RESULT_ZIP))\n')
    # Từ bước cài thư viện trở đi, đưa cả stdout/stderr vào notebook và log.
    # subprocess.run kế thừa FD của kernel Colab có thể chỉ hiện CalledProcessError.
    for index, cell in enumerate(cells):
        text = ''.join(cell['source']).replace('nlp_dia_chi_colab_v1.zip', bundle_name)
        if cell['cell_type'] == 'code' and index >= 6:
            text = text.replace('subprocess.run(', 'run_visible(')
            text = text.replace(', check=True)', f', log_path=LOG_DIR / "cell-{index:02d}.log")')
            text = ('from colab.notebook_runner import run_visible\n'
                    'LOG_DIR = Path(globals().get("DRIVE_ROOT", PROJECT)) / "logs"\n' + text)
        cell['source'] = text.splitlines(keepends=True)
    return {'nbformat': 4, 'nbformat_minor': 5,
            'metadata': {'accelerator': 'GPU', 'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                         'language_info': {'name': 'python'}, 'colab': {'name': 'ViDeBERTa_Colab.ipynb', 'provenance': []}},
            'cells': [dict(c, id=f'cell-{i:02d}') for i, c in enumerate(cells)]}


def build(version='v1'):
    if version not in ('v1', 'v2'):
        raise ValueError('Phiên bản gói không hợp lệ')
    out = ROOT / 'colab/dist'
    out.mkdir(exist_ok=True)
    project = out / ('nlp_dia_chi_colab' if version == 'v1' else version + '/nlp_dia_chi_colab')
    if project.exists():
        raise FileExistsError('Bundle đã có; không ghi đè bản đã bàn giao')
    project.mkdir(parents=True)
    files = [*list((ROOT / 'src').glob('*.py')), *list((ROOT / 'danh_gia').glob('*.py')),
             *list((ROOT / 'colab').glob('*.py')), ROOT / 'colab/requirements.txt', ROOT / 'colab/README.md']
    files += [ROOT / 'tests' / n for n in ('test_pipeline.py', 'test_pipeline_v3.py', 'test_crf.py', 'test_danh_gia.py', 'test_char.py', 'test_videberta_colab.py', 'test_colab_drive.py', 'test_colab_portable.py')]
    if (ROOT / 'colab/kiem_tra/TOKENIZER_SNAPSHOT.json').exists():
        files.append(ROOT / 'colab/kiem_tra/TOKENIZER_SNAPSHOT.json')
    for file in files:
        dest = project / file.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
    (project / 'tests/__init__.py').write_text('', encoding='utf-8')
    base = ROOT / 'mo_hinh/thu_nghiem/char_v1_01'
    for name in ('data', 'snapshot'):
        shutil.copytree(base / name, project / 'bundle_data' / name)
    shutil.copytree(base / 'snapshot/clean', project / 'data/clean')
    crf = ROOT / 'mo_hinh/thu_nghiem/crf_v1_01/train_ket_hop.crfsuite'
    dest = project / crf.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(crf, dest)
    shutil.copy2(ROOT / 'colab/README.md', project / 'HUONG_DAN.md')
    nb = notebook('nlp_dia_chi_colab_' + version + '.zip')
    text = json.dumps(nb, ensure_ascii=False, indent=2)
    (ROOT / 'colab/ViDeBERTa_Colab.ipynb').write_text(text, encoding='utf-8', newline='\n')
    (project / 'ViDeBERTa_Colab.ipynb').write_text(text, encoding='utf-8', newline='\n')
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), '<colab-cell>', 'exec')
    contents = {str(p.relative_to(project)).replace('\\', '/'): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
                for p in project.rglob('*') if p.is_file()}
    manifest = {'bundle_version': version, 'model': 'Fsoft-AIC/videberta-xsmall', 'revision': '029b6b1b1d7636221bd2d1a98b46a2fdba3af34e',
                'files': contents, 'test_dataset_included': False, 'pretrained_weights_included': False,
                'note': 'Notebook tải checkpoint public trực tiếp trên Colab; giữ PyTorch CUDA của runtime.'}
    (project / 'BUNDLE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    archive = out / ('nlp_dia_chi_colab_' + version + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in project.rglob('*'):
            if p.is_file():
                z.write(p, 'nlp_dia_chi_colab/' + str(p.relative_to(project)).replace('\\', '/'))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name, meta in contents.items():
            assert hashlib.sha256(z.read('nlp_dia_chi_colab/' + name)).hexdigest() == meta['sha256']
    print(json.dumps({'zip': str(archive), 'mib': archive.stat().st_size / 2**20, 'files': len(contents) + 1,
                      'notebook_code_cells_compile': True}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
    build(parser.parse_args().version)
