"""Chạy thử: py -3.12 -m src 'địa chỉ' [--beam 40]."""

import argparse
import json
from dataclasses import asdict
from .chuan_hoa import BoChuanHoa


def main():
    p = argparse.ArgumentParser(description="Bản thử chuẩn hóa địa chỉ offline")
    p.add_argument("dia_chi")
    p.add_argument("--beam", type=int, default=40)
    p.add_argument('--crf-model', help='Đường dẫn mô hình CRF đã train; bỏ qua để chạy luật v3')
    p.add_argument('--crf-protected', action='store_true', help='Đối chứng giữ bộ lọc ứng viên v3')
    p.add_argument('--char-model', help='Checkpoint Char-CNN + CRF chạy CPU')
    p.add_argument('--videberta-model', help='Thư mục ViDeBERTa đã fine-tune từ Colab, chạy CPU')
    p.add_argument('--ranker', help='LightGBM ranker đã train cùng checkpoint bộ nhận diện')
    p.add_argument('--tu-dien-duong', help='JSON tra tên đường từ train, tùy chọn thử nghiệm')
    p.add_argument('--bao-ve-duong', action='store_true', help='Thử bảo vệ span đường có tiền tố khỏi ứng viên admin không tiền tố')
    p.add_argument('--threads', type=int, default=1, help='Số luồng CPU cho Char-CNN')
    args = p.parse_args()
    backend = None
    if sum(bool(x) for x in (args.char_model, args.crf_model, args.videberta_model)) > 1:
        p.error('Chỉ chọn một bộ nhận diện: --char-model / --crf-model / --videberta-model')
    if args.ranker and not (args.char_model or args.videberta_model):
        p.error('--ranker cần --char-model hoặc --videberta-model')
    if args.crf_model:
        from .crf_chi_tiet import BoTachCRF
        backend = BoTachCRF(args.crf_model, bao_ve_chi_tiet=args.crf_protected)
    if args.char_model:
        from .char_cnn import BoTachCharCNN
        backend = BoTachCharCNN(args.char_model, threads=args.threads)
    if args.videberta_model:
        from .videberta import BoTachViDeberta
        backend = BoTachViDeberta(args.videberta_model, threads=args.threads)
    dm, ranker = None, None
    if args.ranker:
        from .danh_muc import DanhMuc
        from .xep_hang import BoXepHang
        dm = DanhMuc()
        ranker = BoXepHang(args.ranker, backend.ma_bam, dm.ma_bam)
    names = None
    if args.tu_dien_duong:
        from .chuan_ten_duong import TuDienDuong
        names = TuDienDuong(args.tu_dien_duong)
    model = BoChuanHoa(danh_muc=dm, beam=args.beam, bo_tach=backend, bo_xep_hang=ranker,
                      tu_dien_duong=names, bao_ve_duong=args.bao_ve_duong)
    result = model.chuan_hoa(args.dia_chi)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
