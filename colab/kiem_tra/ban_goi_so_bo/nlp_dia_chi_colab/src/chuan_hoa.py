"""Ghép cả pipeline: chuan_hoa(chuoi) -> KetQua."""

from .danh_muc import DanhMuc
from .kieu_du_lieu import KetQua
from .tim_kiem import dung_trie, sinh_ung_vien
from .tien_xu_ly import token_co_vi_tri, bo_dau
from .giai_ma import tim_duong_di
from .tach_phan_con import tach_co_dau_vet, FIELDS
from .chuyen_doi import tap_dich, sang_cay_moi
from .quy_tac import cac_tien_to


class BoChuanHoa:
    PHIEN_BAN = "baseline_luat_v3"
    def __init__(self, danh_muc: DanhMuc | None = None, beam: int = 40, bo_tach=None, bo_xep_hang=None):
        if bo_xep_hang is not None and not hasattr(bo_tach, 'chuan_bi_chuoi'):
            raise ValueError('Ranker thử nghiệm cần bộ nhận diện có đầu ra ký tự')
        self.danh_muc = danh_muc or DanhMuc()
        if beam < 1:
            raise ValueError("beam phải >= 1")
        self.beam = beam
        self.bo_tach = bo_tach
        self.bo_xep_hang = bo_xep_hang
        if bo_tach is not None:
            self.PHIEN_BAN = getattr(bo_tach, 'phien_ban', 'thu_nghiem_crf_v1_' + ('bao_ve' if bo_tach.bao_ve_chi_tiet else 'mo'))
        if bo_xep_hang is not None:
            self.PHIEN_BAN += '_lambdarank'
        self.trie = dung_trie(self.danh_muc)
        self.tra_cuu_neural = None
        if hasattr(bo_tach, 'chuan_bi_chuoi'):
            from .tra_cuu_neural import TraCuuNeural
            self.tra_cuu_neural = TraCuuNeural(self.danh_muc)

    def tao_gia_thuyet(self, chuoi):
        """Dùng cùng đường sinh giả thuyết cho train ranker và inference."""
        if not isinstance(chuoi, str):
            raise TypeError("Địa chỉ phải là chuỗi")
        records = token_co_vi_tri(chuoi)
        crf_context = None
        if hasattr(self.bo_tach, 'chuan_bi_chuoi'):
            crf_context = self.bo_tach.chuan_bi_chuoi(chuoi)
            records = crf_context.records
        tokens = [t.chu for t in records]
        dm = self.danh_muc
        candidates = sinh_ung_vien(tokens, self.trie, bao_ve_chi_tiet=self.bo_tach is None or self.bo_tach.bao_ve_chi_tiet)
        if self.tra_cuu_neural is not None:
            candidates = self.tra_cuu_neural.mo_rong(crf_context, tokens, self.trie, candidates)
        if crf_context is None and self.bo_tach is not None:
            crf_context = self.bo_tach.chuan_bi(tokens)
        admin_spans = {(u.bat_dau, u.ket_thuc) for u in candidates if u.co_tien_to and u.kieu_khop != "sai_chinh_ta"}
        prefixes = {i: p for i, p in cac_tien_to(tokens).items() if not any(a < i < b for a, b in admin_spans)}
        paths = tim_duong_di(candidates, len(tokens), dm, self.beam)
        ranked = []
        for path in paths:
            occupied = {i for u in path.ung_vien for i in range(u.bat_dau, u.ket_thuc)}
            detail, spans, unknown, inferred = (crf_context.tach(occupied) if crf_context is not None
                                                else tach_co_dau_vet(tokens, occupied, prefixes))
            # Xét cả phần chi tiết trên từng giả thuyết, không nối các khoảng rời.
            score = path.diem - .12*len(unknown) + .05*sum(s["ket_thuc"]-s["bat_dau"] for s in spans)
            if crf_context is not None:
                # Tổng log marginal O của token dùng làm hành chính là đặc trưng
                # ghép đặt tay, không phải xác suất độc lập của cả địa chỉ.
                score += crf_context.diem_hanh_chinh(occupied)
                if hasattr(crf_context, 'diem_ung_vien'):
                    score += sum(crf_context.diem_ung_vien(u) for u in path.ung_vien)
            ranked.append((score, path, detail, spans, unknown, inferred))
        return records, candidates, crf_context, ranked

    def chuan_hoa(self, chuoi: str) -> KetQua:
        records, candidates, crf_context, ranked = self.tao_gia_thuyet(chuoi)
        tokens = [t.chu for t in records]
        dm = self.danh_muc
        if self.bo_xep_hang is not None:
            from .xep_hang import dac_trung_gia_thuyet
            features = [dac_trung_gia_thuyet(x, tokens, candidates, dm, crf_context) for x in ranked]
            scores = self.bo_xep_hang.cham_diem(features)
            ranked = [(float(s), *item[1:]) for s, item in zip(scores, ranked)]
        ranked.sort(key=lambda x: -x[0])
        score, best, detail, spans, unknown, inferred = ranked[0]
        margin = self.bo_xep_hang.nguong_gan if self.bo_xep_hang is not None else .65
        close = [x for x in ranked if score-x[0] <= margin]
        target_sets = [tap_dich(x[1], dm) for x in close]
        wards, provinces = tap_dich(best, dm)
        ma_xa, ma_tinh, warnings = sang_cay_moi(best, detail, dm)
        outcomes = {(tuple(sorted(w)), tuple(sorted(p))) for w, p in target_sets}
        if len(outcomes) > 1:
            warnings.append("nhieu_cach_hieu")
            if len({u.cay for x in close for u in x[1].ung_vien if u.cap == "xa"}) > 1:
                warnings.append("mo_ho_moc_cu_moi")
            # Chỉ khẳng định thành phần được các giả thuyết gần nhất đồng thuận.
            if len({tuple(sorted(w)) for w, _ in target_sets}) > 1:
                ma_xa = ""
            positive_provinces = set().union(*(p for _, p in target_sets))
            # Nhánh bỏ qua tỉnh không được xem là bằng chứng phủ định tỉnh.
            ma_tinh = next(iter(positive_provinces)) if len(positive_provinces) == 1 else ""
        all_wards = set().union(*(w for w, _ in target_sets))
        if len(wards) > 1:
            warnings.append("xa_bi_chia")
        occupied = {i for u in best.ung_vien for i in range(u.bat_dau, u.ket_thuc)}
        if any(u.co_tien_to and u.kieu_khop != "sai_chinh_ta" and not occupied.intersection(range(u.bat_dau, u.ket_thuc)) for u in candidates):
            warnings.append("mau_thuan_hanh_chinh")
        if any(u.kieu_khop == "sai_chinh_ta" for u in best.ung_vien):
            warnings.append("khop_gan_dung")
        if any(u.kieu_khop == "khac_dau" for u in best.ung_vien):
            warnings.append("dau_ten_khac_danh_muc")
        if any(u.kieu_khop == "khac_loai" for u in best.ung_vien):
            warnings.append("loai_hanh_chinh_khac_danh_muc")
        if unknown:
            warnings.append("phan_chua_phan_loai")
        if any(getattr(crf_context, 'lookup_stats', {}).get(k) for k in ('truncated_spans', 'truncated_lookups')):
            warnings.append('ung_vien_tra_cuu_bi_gioi_han')
        if inferred:
            warnings.append("loai_duong_suy_tu_crf" if crf_context is not None else "duong_suy_tu_vi_tri")
        if any(c in detail["so_nha"] for c in "/-–—;"):
            warnings.append("so_nha_can_duyet")
        if not ma_xa:
            warnings.append("thieu_xa")
        if not ma_tinh:
            warnings.append("thieu_tinh")
        elif not any(u.cap == "tinh" for u in best.ung_vien):
            warnings.append("thieu_tinh_dau_vao")
        if not chuoi.strip():
            warnings.append("dau_vao_rong")
        # Không phục hồi dấu tên đường/thôn khi chưa có từ điển chứng thực.
        for f in ("duong", "thon_xom"):
            name = detail[f].split(" ", 1)[-1] if detail[f] else ""
            if any(c.isalpha() for c in name) and bo_dau(name) == name.casefold():
                warnings.append("ten_chi_tiet_chua_xac_minh_dau")
        result = KetQua(**{f: detail[f] for f in FIELDS},
                        ma_xa=ma_xa, ma_tinh=ma_tinh,
                        xa_phuong=dm.ten_day_du("moi", ma_xa) if ma_xa else "",
                        tinh=dm.ten_day_du("moi", ma_tinh) if ma_tinh else "",
                        canh_bao=list(dict.fromkeys(warnings)),
                        phan_chua_phan_loai=detail["phan_chua_phan_loai"])
        result.dia_chi_chuan = ", ".join(getattr(result, f) for f in (*FIELDS, "xa_phuong", "tinh") if getattr(result, f))
        if not ma_xa:
            result.xa_moi_ung_vien = [{"ma_xa": w, "ten": dm.ten_day_du("moi", w), "ma_tinh": dm.lay("moi", w).ma_cha} for w in sorted(all_wards)]
        def trace(a, b, **extra):
            return {"token_bat_dau": a, "token_ket_thuc": b, "ky_tu_bat_dau": records[a].bat_dau,
                    "ky_tu_ket_thuc": records[b-1].ket_thuc,
                    "doan_goc": chuoi[records[a].bat_dau:records[b-1].ket_thuc], **extra}
        for u in sorted(best.ung_vien, key=lambda u: u.bat_dau):
            result.dau_vet.append(trace(u.bat_dau, u.ket_thuc, truong=u.cap, ma=u.ma, moc=u.cay, kieu_khop=u.kieu_khop, diem=u.diem))
        for s in spans:
            result.dau_vet.append(trace(s["bat_dau"], s["ket_thuc"], truong=s["truong"], gia_tri=s["gia_tri"], kieu_khop="crf" if crf_context is not None else "luat"))
        result.thong_ke = {"so_token": len(tokens), "so_ung_vien": len(candidates), "so_gia_thuyet": len(ranked),
                          "so_cach_hieu_gan_nhat": len(close), "so_ket_qua_dich_gan_nhat": len(outcomes), "diem": round(score, 4),
                          "moc_dich": "2025-07-01", "mo_hinh": "crf_va_diem_ghep_tay" if crf_context is not None else "luat_va_diem_tay"}
        if crf_context is not None:
            result.thong_ke['crf_model_sha256'] = self.bo_tach.ma_bam
            result.thong_ke['crf_bio_loi_truoc_sua'] = crf_context.loi_bio
        if hasattr(self.bo_tach, 'phien_ban'):
            result.thong_ke['mo_hinh'] = getattr(self.bo_tach, 'ten_mo_hinh', 'char_cnn_crf') + '_va_diem_tay'
            result.thong_ke['diem_nhan_dien'] = 'log_softmax_emission_khong_phai_marginal_CRF'
            result.thong_ke['tra_cuu_neural'] = crf_context.lookup_stats
            if hasattr(crf_context, 'segmentation_fallback'):
                result.thong_ke['tach_tu_fallback_raw'] = crf_context.segmentation_fallback
        if self.bo_xep_hang is not None:
            result.thong_ke['mo_hinh'] = getattr(self.bo_tach, 'ten_mo_hinh', 'char_cnn_crf') + '_va_lambdarank'
            result.thong_ke['ranker_sha256'] = self.bo_xep_hang.ma_bam
            result.thong_ke['diem_khong_phai_xac_suat'] = True
        result.thong_ke["phien_ban"] = self.PHIEN_BAN
        return result
