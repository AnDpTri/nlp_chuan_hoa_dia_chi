"""Đẩy stdout/stderr subprocess ra notebook, lưu log và giữ exit code lỗi."""

from pathlib import Path
import subprocess
import sys


def run_visible(command, *, cwd=None, log_path=None):
    output = None
    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        output = path.open('a', encoding='utf-8', newline='\n')
    try:
        with subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                              bufsize=1) as process:
            try:
                for line in process.stdout:
                    print(line, end='', flush=True)
                    if output:
                        output.write(line)
                        output.flush()
                returncode = process.wait()
            except BaseException:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                raise
        if returncode:
            raise subprocess.CalledProcessError(returncode, command)
        return subprocess.CompletedProcess(command, returncode)
    finally:
        if output:
            output.close()
