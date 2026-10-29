"""Train ranker trên train riêng, đánh giá ViDeBERTa CPU và đối chứng."""

import argparse
import json
from pathlib import Path

from src.videberta import BoTachViDeberta
from danh_gia.huan_luyen_char import train_ranker
from danh_gia.do_char import evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    meta = json.loads((args.run_dir / 'training.json').read_text(encoding='utf-8'))
    if not meta['training_complete']:
        raise ValueError('Chưa hoàn thành toàn bộ số epoch đã định; không chọn checkpoint bằng dev')
    extractor = BoTachViDeberta(args.run_dir / 'model', device='cpu', threads=1)
    if (args.run_dir / 'ranker.txt').exists():
        from src.xep_hang import BoXepHang
        from src.danh_muc import DanhMuc
        dm = DanhMuc(args.run_dir / 'snapshot/clean')
        BoXepHang(args.run_dir / 'ranker.txt', extractor.ma_bam, dm.ma_bam)
        print('Giữ ranker đã train cùng checkpoint.', flush=True)
    else:
        train_ranker(args.run_dir, extractor=extractor)
    if args.output.exists():
        raise FileExistsError('Đã có báo cáo. Chọn đường dẫn mới để giữ lịch sử đo.')
    evaluate(args.run_dir, args.output, extractor=extractor, mode_prefix='videberta')
    # Đây là CPU Colab; không gắn số đo này cho CPU laptop.
    report_file = args.output / 'thong_ke.json'
    report = json.loads(report_file.read_text(encoding='utf-8'))
    report['benchmark_host'] = 'CPU của runtime đang chạy; khi chạy notebook là CPU Colab, không phải i5-11400H'
    report['training_device'] = meta['device']
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
