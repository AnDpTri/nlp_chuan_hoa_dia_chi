"""Nhật ký phiên chạy thử: ghi mỗi lần chuẩn hóa và mỗi lần người dùng báo sai vào JSONL cục bộ.

Chỉ bật khi biến môi trường AMC_LOG=1 (CONTRACT.md: mặc định không log địa chỉ thô).
File: api/logs/phien_YYYYMMDD.jsonl, một dòng một sự kiện, để đọc lại và phân tích lỗi.
"""

import json
import os
import threading
import time
import traceback
import uuid
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
_lock = threading.Lock()


def bat() -> bool:
    return os.environ.get("AMC_LOG") == "1"


def ghi(loai: str, du_lieu: dict) -> str | None:
    """Ghi một sự kiện; trả về log_id (None nếu log tắt). Lỗi ghi log không được làm hỏng request."""
    if not bat():
        return None
    log_id = uuid.uuid4().hex[:12]
    dong = {"log_id": log_id, "loai": loai, "thoi_gian": time.strftime("%Y-%m-%dT%H:%M:%S"), **du_lieu}
    try:
        LOG_DIR.mkdir(exist_ok=True)
        tep = LOG_DIR / time.strftime("phien_%Y%m%d.jsonl")
        with _lock, open(tep, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(dong, ensure_ascii=False) + "\n")
    except OSError:
        return None
    return log_id


def ghi_loi(dau_vao: str, loi: Exception) -> str | None:
    return ghi("loi_xu_ly", {"input": dau_vao, "loi": repr(loi), "traceback": traceback.format_exc()})
