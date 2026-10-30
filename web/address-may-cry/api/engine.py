"""Module adapter bọc pipeline chuẩn hóa địa chỉ NLP (Address May Cry).
Khởi tạo model 1 lần (Singleton), chạy CPU 1 thread, bảo vệ thread-safe với Lock.
Hoàn toàn tuân thủ hợp đồng CONTRACT.md và src/shared/contracts.ts.
"""

import os
import sys
import time
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Xác định project root động (D:\nlp_chuan_hoa_dia_chi)
API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Đặt số thread torch trước khi nạp
import torch
torch.set_num_threads(1)

from src.danh_muc import DanhMuc
from src.char_cnn import BoTachCharCNN
from src.xep_hang import BoXepHang
from src.chuan_ten_duong import TuDienDuong
from src.chuan_hoa import BoChuanHoa
from src.kieu_du_lieu import KetQua


class NlpEngineAdapter:
    """Adapter bọc BoChuanHoa singleton và thread-safe cho HTTP API."""

    _instance: Optional["NlpEngineAdapter"] = None
    _init_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.Lock()
        self.status = "loading"
        self.error_message: Optional[str] = None
        self.engine_name = "CNN v2 (char_v2_01) + Ranker v2 + Dict v5 (CPU 1 thread)"
        self.target_date = "2025-07-01"
        self._pipe: Optional[BoChuanHoa] = None
        self._dm: Optional[DanhMuc] = None
        self._cnn: Optional[BoTachCharCNN] = None
        self._ranker: Optional[BoXepHang] = None
        self._tdd: Optional[TuDienDuong] = None

        self._load_models()

    def _load_models(self) -> None:
        try:
            clean_dir = PROJECT_ROOT / "data" / "clean"
            cnn_path = PROJECT_ROOT / "mo_hinh" / "thu_nghiem" / "char_v2_01" / "char_cnn.pt"
            ranker_path = PROJECT_ROOT / "mo_hinh" / "thu_nghiem" / "char_v2_01" / "ranker.txt"
            dict_path = PROJECT_ROOT / "danh_gia" / "ket_qua" / "tu_dien_duong_v5.json"

            if not clean_dir.exists():
                raise FileNotFoundError(f"Không tìm thấy thư mục danh mục: {clean_dir}")
            if not cnn_path.exists():
                raise FileNotFoundError(f"Không tìm thấy checkpoint CharCNN: {cnn_path}")
            if not ranker_path.exists():
                raise FileNotFoundError(f"Không tìm thấy checkpoint Ranker: {ranker_path}")
            if not dict_path.exists():
                raise FileNotFoundError(f"Không tìm thấy từ điển đường v5: {dict_path}")

            self._dm = DanhMuc(clean_dir)
            self._cnn = BoTachCharCNN(cnn_path, threads=1)
            self._ranker = BoXepHang(ranker_path, self._cnn.ma_bam, self._dm.ma_bam)
            self._tdd = TuDienDuong(dict_path)

            self._pipe = BoChuanHoa(
                self._dm,
                bo_tach=self._cnn,
                bo_xep_hang=self._ranker,
                tu_dien_duong=self._tdd,
                bao_ve_duong=True,
                tien_to_mac_dinh=True,
            )

            # Warm-up 1 câu ngắn để khởi tạo bộ nhớ torch
            with self._lock:
                _ = self._pipe.chuan_hoa("Hà Nội")

            self.status = "ok"
            self.error_message = None
        except Exception as e:
            self.status = "error"
            self.error_message = f"Lỗi khởi tạo NLP Engine: {type(e).__name__}"
            self._pipe = None

    @classmethod
    def get_instance(cls) -> "NlpEngineAdapter":
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def is_ready(self) -> bool:
        return self.status == "ok" and self._pipe is not None

    def normalize(self, address: str) -> Tuple[Dict[str, Any], float, str]:
        """Chuẩn hóa một địa chỉ đơn.

        Returns:
            Tuple[Dict[str, Any], float, str]:
                - result: dict tương thích AddressResult
                - elapsed_ms: thời gian đo thực tế (ms)
                - status: 'processed' hoặc 'needs_review'
        """
        if not self.is_ready():
            raise RuntimeError("Engine chưa sẵn sàng hoặc đã gặp lỗi khởi tạo.")

        t0 = time.perf_counter()
        with self._lock:
            res: KetQua = self._pipe.chuan_hoa(address)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        res_dict = asdict(res)

        # Đánh giá status: 'needs_review' khi có cảnh báo, nhiều xã mới ứng viên (mơ hồ),
        # hoặc có phần chưa phân loại đáng kể, hoặc thiếu mã hành chính.
        canh_bao = res_dict.get("canh_bao") or []
        xa_moi_ung_vien = res_dict.get("xa_moi_ung_vien") or []
        phan_chua_phan_loai = (res_dict.get("phan_chua_phan_loai") or "").strip()
        ma_tinh = (res_dict.get("ma_tinh") or "").strip()
        ma_xa = (res_dict.get("ma_xa") or "").strip()

        needs_review = (
            len(canh_bao) > 0
            or len(xa_moi_ung_vien) > 1
            or bool(phan_chua_phan_loai)
            or not ma_tinh
            or not ma_xa
        )

        status = "needs_review" if needs_review else "processed"
        return res_dict, round(elapsed_ms, 2), status
