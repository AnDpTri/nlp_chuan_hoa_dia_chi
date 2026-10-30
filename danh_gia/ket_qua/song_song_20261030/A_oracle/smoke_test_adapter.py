import sys
from pathlib import Path
ROOT = Path("D:/nlp_chuan_hoa_dia_chi")
sys.path.insert(0, str(ROOT))

import csv
import copy
import unicodedata

from src.danh_muc import DanhMuc
from src.char_cnn import BoTachCharCNN
from src.xep_hang import BoXepHang, dac_trung_gia_thuyet
from src.chuan_ten_duong import TuDienDuong
from src.chuan_hoa import BoChuanHoa

def norm(s):
    if s is None:
        return ""
    return " ".join(unicodedata.normalize("NFC", str(s)).casefold().split())

CORE = ["so_nha", "ngo_ngach_hem", "thon_xom", "duong", "ma_xa", "ma_tinh"]

class ReplayBoChuanHoa(BoChuanHoa):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_precomputed = None
        self._override_ranked = None

    def set_precomputed(self, records, candidates, crf_context, ranked):
        self._cached_precomputed = (records, candidates, crf_context, ranked)

    def tao_gia_thuyet(self, chuoi: str):
        if self._override_ranked is not None:
            records, candidates, crf_context, _ = self._cached_precomputed
            return (
                copy.deepcopy(records),
                copy.deepcopy(candidates),
                crf_context,
                copy.deepcopy(self._override_ranked)
            )
        return super().tao_gia_thuyet(chuoi)

def run_smoke():
    dm = DanhMuc()
    cnn = BoTachCharCNN(ROOT / "mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt", threads=1)
    rk = BoXepHang(ROOT / "mo_hinh/thu_nghiem/char_v2_01/ranker.txt", cnn.ma_bam, dm.ma_bam)
    td = TuDienDuong(ROOT / "danh_gia/ket_qua/tu_dien_duong_v5.json")

    pipe_runtime = BoChuanHoa(dm, bo_tach=cnn, bo_xep_hang=rk, tu_dien_duong=td,
                              bao_ve_duong=True, tien_to_mac_dinh=True)
    pipe_replay = ReplayBoChuanHoa(dm, bo_tach=cnn, bo_xep_hang=rk, tu_dien_duong=td,
                                  bao_ve_duong=True, tien_to_mac_dinh=True)

    with open(ROOT / "data/train_dev/dev.csv", "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))[:20]

    parity_matches = 0
    total = len(rows)

    for i, r in enumerate(rows):
        inp = r["dau_vao"]
        # 1. Run actual runtime
        res_real = pipe_runtime.chuan_hoa(inp)

        # 2. Precompute once with CNN
        records, candidates, crf_context, ranked_base = pipe_runtime.tao_gia_thuyet(inp)
        tokens = [t.chu for t in records]
        features = [dac_trung_gia_thuyet(x, tokens, candidates, dm, crf_context) for x in ranked_base]
        scores = rk.cham_diem(features)
        ranked_lgb = [(float(s), *item[1:]) for s, item in zip(scores, ranked_base)]
        ranked_lgb.sort(key=lambda x: -x[0])

        # 3. Replay with the adapter passing ranked_lgb
        # Since ranked_lgb is already scored by ranker, we can pass it to pipe_replay
        # but wait: pipe_replay.chuan_hoa would re-run ranker if bo_xep_hang is set!
        # To avoid re-running ranker inside chuan_hoa when already scored:
        pipe_replay.set_precomputed(records, candidates, crf_context, ranked_base)
        pipe_replay._override_ranked = ranked_base
        res_replay = pipe_replay.chuan_hoa(inp)

        # Check parity
        pred_real = {f: getattr(res_real, f) for f in CORE}
        pred_rep = {f: getattr(res_replay, f) for f in CORE}
        if all(pred_real[f] == pred_rep[f] for f in CORE):
            parity_matches += 1
        else:
            print(f"Mismatch at sample {i}:")
            print(f"  Real:   {pred_real}")
            print(f"  Replay: {pred_rep}")

    print(f"Parity check: {parity_matches}/{total} matches.")

if __name__ == "__main__":
    run_smoke()
