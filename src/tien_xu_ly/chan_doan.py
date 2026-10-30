"""Chẩn đoán tiền xử lý: dựng bản ghi các bước trung gian (CRF, ứng viên, giả thuyết, khôi phục đường)
để đọc lại khi kết quả sai. Chỉ đọc, không đổi kết quả."""

from collections import defaultdict

SO_UNG_VIEN_MOI_DOAN = 8
SO_GIA_THUYET = 5


def _don_vi(u, dm):
    d = dm.lay(u.cay, u.ma)
    return {"cap": u.cap or d.cap, "ma": u.ma, "cay": u.cay, "ten": f"{d.loai} {d.ten}", "ma_cha": d.ma_cha,
            "kieu_khop": u.kieu_khop, "diem": round(u.diem, 3), "co_tien_to": u.co_tien_to,
            "token": [u.bat_dau, u.ket_thuc]}


def _ung_vien_theo_doan(candidates, tokens, dm):
    """Gom ứng viên theo đoạn token; mỗi đoạn giữ tổng số và vài ứng viên điểm cao nhất."""
    nhom = defaultdict(list)
    for u in candidates:
        nhom[(u.bat_dau, u.ket_thuc)].append(u)
    out = []
    for (a, b), us in sorted(nhom.items()):
        us = sorted(us, key=lambda u: -u.diem)
        out.append({"doan": " ".join(tokens[a:b]), "token": [a, b], "so_ung_vien": len(us),
                    "top": [_don_vi(u, dm) for u in us[:SO_UNG_VIEN_MOI_DOAN]]})
    return out


def tao_chan_doan(sach, noi_bo, dm) -> dict:
    tokens = [t.chu for t in noi_bo.records]
    ctx = noi_bo.crf_context
    crf = [{"truong": r, "doan": sach.chuoi[a:b], "ky_tu": [a, b]} for r, a, b in getattr(ctx, "char_spans", ()) or ()]
    gia_thuyet = []
    for diem, path, detail, _spans, unknown, inferred in noi_bo.ranked[:SO_GIA_THUYET]:
        gia_thuyet.append({"diem": round(float(diem), 4), "cay": path.cay,
                           "don_vi": [_don_vi(u, dm) for u in path.ung_vien],
                           "chi_tiet": {k: v for k, v in detail.items() if v},
                           "chua_phan_loai": unknown, "suy_ra": inferred})
    truoc = noi_bo.chi_tiet_truoc_duong
    sau = {k: getattr(sach, k) for k in ("so_nha", "ngo_ngach_hem", "thon_xom", "duong", "phan_chua_phan_loai")}
    return {
        "token": tokens,
        "crf": crf,
        "ung_vien": _ung_vien_theo_doan(noi_bo.candidates, tokens, dm),
        "so_gia_thuyet": len(noi_bo.ranked),
        "so_gia_thuyet_gan": len(noi_bo.close),
        "gia_thuyet": gia_thuyet,
        "khoi_phuc_duong": {k: {"truoc": truoc.get(k, ""), "sau": v} for k, v in sau.items() if truoc.get(k, "") != v},
        "canh_bao_giua": list(sach.canh_bao_giua),
        "canh_bao_sau": list(sach.canh_bao_sau),
    }
