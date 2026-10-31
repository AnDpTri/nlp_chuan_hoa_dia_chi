#!/bin/bash
# Dùng (từ gốc repo): bash danh_gia/v3/train_va_do.sh <ten_run> <lap_goc>
# Chuẩn bị dữ liệu -> train CNN -> train ranker -> chạy dev + bộ khó -> chấm điểm.
# Thư mục chạy nằm ở rieng/train_v3/<ten_run> (không lên git).
set -e
TEN=$1; LAP=${2:-1}
GOC=$(cd "$(dirname "$0")/../.." && pwd)
PY=${PY:-$GOC/.venv-neural/Scripts/python.exe}
RUN=$GOC/rieng/train_v3
mkdir -p "$RUN"
cd "$RUN"
$PY -X utf8 -B "$GOC/danh_gia/v3/chuan_bi.py" $TEN $LAP > $TEN.prep.log 2>&1
cd "$GOC"
$PY -X utf8 -B -m danh_gia.huan_luyen_char --run-dir "$RUN/$TEN" --stage cnn --threads 4 > "$RUN/$TEN.cnn.log" 2>&1
$PY -X utf8 -B -m danh_gia.huan_luyen_char --run-dir "$RUN/$TEN" --stage ranker --threads 4 > "$RUN/$TEN.ranker.log" 2>&1
cd "$RUN"
$PY -X utf8 -B "$GOC/danh_gia/v3/chay_mo_hinh.py" $TEN/char_cnn.pt $TEN/ranker.txt ket_$TEN > $TEN.eval.log 2>&1
$PY -X utf8 "$GOC/danh_gia/v3/do_tien_xu_ly.py" file ket_$TEN/ket_qua.jsonl > $TEN.diem.txt 2>&1
echo "XONG $TEN"
