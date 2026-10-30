"""Script dừng an toàn Address May Cry API Server dựa trên PID ghi nhận.
Tránh dừng theo tên tiến trình để không ảnh hưởng tới các phiên làm việc song song khác.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Cấu hình utf-8 console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

API_DIR = Path(__file__).resolve().parent
PID_FILE = API_DIR / "server.pid"


def stop_server():
    if not PID_FILE.exists():
        print("[THÔNG BÁO] Không tìm thấy tệp server.pid. Máy chủ có thể chưa khởi động hoặc đã dừng.")
        return

    pid_str = PID_FILE.read_text().strip()
    try:
        pid = int(pid_str)
    except ValueError:
        print(f"[LỖI] Nội dung PID không hợp lệ: '{pid_str}'.")
        PID_FILE.unlink(missing_ok=True)
        return

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Đang dừng tiến trình API Server (PID: {pid})...")

    # Kiểm tra xem tiến trình có đang chạy không
    is_running = False
    if sys.platform == "win32":
        try:
            output = subprocess.check_output(f"tasklist /FI \"PID eq {pid}\"", shell=True).decode("utf-8", errors="ignore")
            if str(pid) in output:
                is_running = True
        except Exception:
            is_running = False
    else:
        try:
            os.kill(pid, 0)
            is_running = True
        except OSError:
            is_running = False

    if not is_running:
        print(f"[THÔNG BÁO] Tiến trình PID {pid} không còn hoạt động.")
        PID_FILE.unlink(missing_ok=True)
        return

    # Dừng tiến trình chính xác bằng PID
    if sys.platform == "win32":
        res = subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[THÀNH CÔNG] Đã dừng tiến trình API Server (PID: {pid}).")
        else:
            print(f"[LỖI] Không thể dừng tiến trình: {res.stderr.strip()}")
    else:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[THÀNH CÔNG] Đã gửi tín hiệu dừng tới PID {pid}.")
        except Exception as e:
            print(f"[LỖI] Không thể dừng tiến trình: {e}")

    PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    stop_server()
