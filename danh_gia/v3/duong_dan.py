"""Đường dẫn dùng chung cho script train/đo v3, tính theo gốc repo.

Đặt CODE_ROOT để đo code ở chỗ khác (ví dụ một worktree thử nghiệm).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_ROOT = Path(os.environ.get('CODE_ROOT', ROOT))
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

CLEAN = ROOT / 'data' / 'clean'
DEV = ROOT / 'data' / 'dev'                      # dev_goc.csv, dev_kho.csv (nhãn gốc)
NHAN_SUA = DEV / 'nhan_sua'                      # nhãn dev đã sửa, dùng để chấm
TEST = ROOT / 'data' / 'test' / 'dia_chi_test.csv'
TU_DIEN_TRAIN = ROOT / 'data' / 'train' / 'tu_dien_train.json'
BO_TRAIN_DAT = ROOT / 'data' / 'train' / 'bo_train' / 'dat'
MO_HINH = ROOT / 'mo_hinh' / 'thu_nghiem'
KET_QUA = ROOT / 'danh_gia' / 'ket_qua'
LOG_WEB = ROOT / 'web' / 'address-may-cry' / 'api' / 'logs'

RIENG = ROOT / 'rieng'                           # không lên git
BO_KHO = RIENG / 'bo_kho'                        # đáp án giữ kín
TRAIN_RUN = RIENG / 'train_v3'                   # thư mục chạy train (dữ liệu sinh ra, checkpoint)
