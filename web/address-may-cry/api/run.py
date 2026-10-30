"""Script khởi động Address May Cry API Server (cổng 8080).
Hỗ trợ chạy nền (daemon/background) hoặc chạy trực tiếp (foreground).
Ghi nhận PID và log để quản lý an toàn, không xung đột với các phiên song song.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
import json
from pathlib import Path

# Cấu hình utf-8 console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent.parent.parent
PYTHON_EXE = PROJECT_ROOT / ".venv-neural" / "Scripts" / "python.exe"
PID_FILE = API_DIR / "server.pid"
LOG_FILE = API_DIR / "api.log"

HOST = "127.0.0.1"
PORT = 8080


def is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def check_health(host: str, port: int) -> bool:
    try:
        url = f"http://{host}:{port}/api/v1/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") in ("ok", "loading")
    except Exception:
        return False


def start_foreground():
    from server import run_server
    run_server(HOST, PORT)


def start_background():
    if not PYTHON_EXE.exists():
        print(f"[LỖI] Không tìm thấy môi trường Python tại: {PYTHON_EXE}")
        sys.exit(1)

    # 1. Kiểm tra nếu server đã chạy sẵn
    if is_port_in_use(HOST, PORT):
        if check_health(HOST, PORT):
            pid_str = PID_FILE.read_text().strip() if PID_FILE.exists() else "Không rõ"
            print(f"[THÔNG BÁO] Address May Cry API Server ĐÃ ĐANG CHẠY tại http://{HOST}:{PORT} (PID: {pid_str}).")
            return
        else:
            print(f"[CẢNH BÁO] Cổng {PORT} đang bị chiếm dụng bởi tiến trình khác. Không thể tự ý tắt tiến trình lạ.")
            print(f"           Vui lòng giải phóng cổng {PORT} hoặc chỉ định cổng khác.")
            sys.exit(1)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Đang khởi động Address May Cry API Server ở chế độ nền...")

    server_script = API_DIR / "server.py"

    # Mở log file để redirect output
    log_f = open(LOG_FILE, "a", encoding="utf-8")

    # Trên Windows: sử dụng creationflags DETACHED_PROCESS để chạy độc lập
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [str(PYTHON_EXE), str(server_script), str(PORT)],
        stdout=log_f,
        stderr=log_f,
        cwd=str(PROJECT_ROOT),
        creationflags=creation_flags,
    )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Tiến trình API đã được khởi tạo với PID: {proc.pid}")
    print(f"                             Nhật ký ghi tại: {LOG_FILE}")

    # Đợi server sẵn sàng tối đa 15s
    print("Đang đợi máy chủ nạp NLP Engine và phản hồi health check...")
    ready = False
    for i in range(30):
        time.sleep(0.5)
        if check_health(HOST, PORT):
            ready = True
            break

    if ready:
        print(f"\n[THÀNH CÔNG] Address May Cry API Server ĐÃ SẴN SÀNG tại: http://{HOST}:{PORT}")
        print(f"            - Endpoint Health: http://{HOST}:{PORT}/api/v1/health")
        print(f"            - Endpoint Normalize: POST http://{HOST}:{PORT}/api/v1/normalize")
        print(f"            - Endpoint Batch: POST http://{HOST}:{PORT}/api/v1/batch")
        print(f"            - Dừng máy chủ bằng lệnh: python web/address-may-cry/api/stop.py")
    else:
        print(f"\n[CẢNH BÁO] Máy chủ chưa phản hồi sau 15 giây. Vui lòng kiểm tra log tại: {LOG_FILE}")


if __name__ == "__main__":
    if "--foreground" in sys.argv:
        start_foreground()
    else:
        start_background()
