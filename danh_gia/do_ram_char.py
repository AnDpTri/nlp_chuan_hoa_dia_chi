"""Đo khởi tạo/RAM neural trong tiến trình riêng, không nạp mô hình đối chứng."""

import argparse
import time
from pathlib import Path

from .chay_ban_thu import memory


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    before = memory()
    start = time.perf_counter()
    from src.tien_xu_ly.char_cnn import BoTachCharCNN
    from src.chuan_hoa import BoChuanHoa
    from src.danh_muc import DanhMuc
    from src.tien_xu_ly.xep_hang import BoXepHang
    from .huan_luyen_char import save_json
    dm = DanhMuc(args.run_dir / 'snapshot/clean')
    extractor = BoTachCharCNN(args.run_dir / 'char_cnn.pt')
    ranker = BoXepHang(args.run_dir / 'ranker.txt', extractor.ma_bam, dm.ma_bam)
    model = BoChuanHoa(danh_muc=dm, bo_tach=extractor, bo_xep_hang=ranker)
    init_seconds = time.perf_counter() - start
    after_init = memory()
    text = 'Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội'
    result = model.chuan_hoa(text)
    for _ in range(20):
        model.chuan_hoa(text)
    report = {'initialization_including_optional_imports_seconds': init_seconds,
              'before_imports': before, 'after_initialization': after_init, 'after_21_addresses': memory(),
              'scope': 'Toàn tiến trình Python/PyTorch/LightGBM, danh mục, trie và model; không phải riêng trọng số. Cache mới chỉ warm một địa chỉ.',
              'example_input': text, 'example_output': result.dia_chi_chuan}
    save_json(args.output, report)
    print(report)


if __name__ == '__main__':
    main()
