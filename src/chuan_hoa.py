"""Ghép cả pipeline: chuan_hoa(chuoi) -> KetQua."""

from .danh_muc import DanhMuc
from .kieu_du_lieu import KetQua
from .tim_kiem import dung_trie, sinh_ung_vien, bo_sung_tu_luoi_goc
from .tien_xu_ly import token_co_vi_tri, bo_dau
from .giai_ma import tim_duong_di
from .tach_phan_con import tach_co_dau_vet, FIELDS
from .chuyen_doi import tap_dich, sang_cay_moi
from .quy_tac import cac_tien_to, CHI_TIET, khop_tien_to
from .phuc_hoi_duong import phuc_hoi_ten_duong, bo_duong_viet_tat_chua_giai


def _token_trong_span_ky_tu(context, token, role):
    """Ghép hai bộ token khác nhau qua offset ký tự gốc, không dùng chỉ số token."""
    return any(r == role and a <= token.bat_dau and token.ket_thuc <= b
               for r, a, b in getattr(context, "char_spans", ()))


def _chuan_chuoi_dia_chi(res: KetQua) -> str:
    parts = []
    if res.so_nha:
        parts.append(res.so_nha if res.so_nha.startswith(("Số ", "Số")) else f"Số {res.so_nha}")
    if res.ngo_ngach_hem:
        parts.append(res.ngo_ngach_hem)
    if res.thon_xom:
        parts.append(res.thon_xom)
    if res.duong:
        road_pfx = ("Đường ", "Phố ", "Quốc lộ ", "Tỉnh lộ ", "Xa lộ ", "Đại lộ ", "ĐT ", "HL ", "Hương lộ ")
        parts.append(res.duong if any(res.duong.startswith(p) for p in road_pfx) else f"Đường {res.duong}")
    if res.xa_phuong:
        parts.append(res.xa_phuong)
    if res.tinh:
        parts.append(res.tinh)
    return ", ".join(parts)


def _tao_dau_vet(records, chuoi, a, b, **extra):
    return {"token_bat_dau": a, "token_ket_thuc": b, "ky_tu_bat_dau": records[a].bat_dau,
            "ky_tu_ket_thuc": records[b-1].ket_thuc,
            "doan_goc": chuoi[records[a].bat_dau:records[b-1].ket_thuc], **extra}


class BoChuanHoa:
    PHIEN_BAN = "baseline_luat_v3"
    def __init__(self, danh_muc: DanhMuc | None = None, beam: int = 40, bo_tach=None, bo_xep_hang=None,
                 tu_dien_duong=None, bao_ve_duong=False, hop_dong=False, tien_to_mac_dinh: bool = True,
                 tien_to_so_nha: bool | None = None, tien_to_duong: bool | None = None):
        if bo_xep_hang is not None and not hasattr(bo_tach, 'chuan_bi_chuoi'):
            raise ValueError('Ranker thử nghiệm cần bộ nhận diện có đầu ra ký tự')
        self.danh_muc = danh_muc or DanhMuc()
        if beam < 1:
            raise ValueError("beam phải >= 1")
        self.beam = beam
        self.bo_tach = bo_tach
        self.bo_xep_hang = bo_xep_hang
        self.tu_dien_duong = tu_dien_duong
        self.bao_ve_duong = bao_ve_duong
        self.hop_dong = hop_dong
        self.tien_to_mac_dinh = tien_to_mac_dinh
        self.tien_to_so_nha = tien_to_mac_dinh if tien_to_so_nha is None else tien_to_so_nha
        self.tien_to_duong = tien_to_mac_dinh if tien_to_duong is None else tien_to_duong
        if bo_tach is not None:
            self.PHIEN_BAN = getattr(bo_tach, 'phien_ban', 'thu_nghiem_crf_v1_' + ('bao_ve' if bo_tach.bao_ve_chi_tiet else 'mo'))
        if bo_xep_hang is not None:
            self.PHIEN_BAN += '_lambdarank'
        if bao_ve_duong:
            self.PHIEN_BAN += '_bao_ve_duong'
        if tu_dien_duong is not None:
            self.PHIEN_BAN += '_ten_train'
        if hop_dong:
            self.PHIEN_BAN += '_hop_dong_v1'
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
        lexical_records = records
        crf_context = None
        if hasattr(self.bo_tach, 'chuan_bi_chuoi'):
            crf_context = self.bo_tach.chuan_bi_chuoi(chuoi)
            records = crf_context.records
        tokens = [t.chu for t in records]
        dm = self.danh_muc
        candidates = sinh_ung_vien(tokens, self.trie, bao_ve_chi_tiet=self.bo_tach is None or self.bo_tach.bao_ve_chi_tiet)
        if self.tra_cuu_neural is not None:
            candidates, lexical_added = bo_sung_tu_luoi_goc(lexical_records, records, self.trie, candidates,
                                                          bao_ve_chi_tiet=self.bo_tach.bao_ve_chi_tiet)
            candidates = self.tra_cuu_neural.mo_rong(crf_context, tokens, self.trie, candidates)
            if lexical_added:
                crf_context.lookup_stats['lexical_added'] = lexical_added
        if crf_context is None and self.bo_tach is not None:
            crf_context = self.bo_tach.chuan_bi(tokens)
        if self.bao_ve_duong and not self.hop_dong and crf_context is not None:
            # Thử nghiệm: không lấy tên hành chính không tiền tố nằm hoàn toàn
            # trong span đường có tiền tố rõ ràng. Giữ ứng viên có tiền tố admin.
            from .crf_chi_tiet import bio_spans
            protected = []
            for field, a, b in bio_spans(crf_context.labels)[0]:
                marker = khop_tien_to(tokens[a:b], 0, CHI_TIET)
                if field == 'duong' and marker and marker[1][0] == 'duong':
                    protected.append((a + marker[0], b))
            candidates = [u for u in candidates if u.co_tien_to or not any(
                a <= u.bat_dau and u.ket_thuc <= b for a, b in protected)]
        admin_spans = {(u.bat_dau, u.ket_thuc) for u in candidates if u.co_tien_to and u.kieu_khop != "sai_chinh_ta"}
        prefixes = {i: p for i, p in cac_tien_to(tokens).items() if not any(a < i < b for a, b in admin_spans)}
        paths = tim_duong_di(candidates, len(tokens), dm, self.beam)
        ranked = []
        for path in paths:
            occupied = {i for u in path.ung_vien for i in range(u.bat_dau, u.ket_thuc)}
            detail, spans, unknown, inferred = (
                crf_context.tach(occupied, tien_to_mac_dinh=self.tien_to_mac_dinh,
                                 tien_to_so_nha=self.tien_to_so_nha, tien_to_duong=self.tien_to_duong)
                if crf_context is not None
                else tach_co_dau_vet(tokens, occupied, prefixes, tien_to_mac_dinh=self.tien_to_mac_dinh,
                                     tien_to_so_nha=self.tien_to_so_nha, tien_to_duong=self.tien_to_duong))
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

    def _chon_gia_thuyet(self, tokens, candidates, crf_context, ranked):
        dm = self.danh_muc
        if self.bo_xep_hang is not None:
            from .xep_hang import dac_trung_gia_thuyet
            features = [dac_trung_gia_thuyet(x, tokens, candidates, dm, crf_context) for x in ranked]
            scores = self.bo_xep_hang.cham_diem(features)
            ranked = [(float(s), *item[1:]) for s, item in zip(scores, ranked)]
        ranked.sort(key=lambda x: -x[0])
        score, best, detail, spans, unknown, inferred = ranked[0]
        margin = self.bo_xep_hang.nguong_gan if self.bo_xep_hang is not None else .65
        close = [x for x in ranked if score - x[0] <= margin]
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
        return (score, best, detail, spans, unknown, inferred, close, outcomes, target_sets, ma_xa, ma_tinh, warnings, wards)

    def _xac_lap_canh_bao(self, warnings, wards, best, candidates, unknown, crf_context, inferred,
                          detail, ma_xa, ma_tinh, chuoi):
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

    def _dung_ket_qua(self, detail, ma_xa, ma_tinh, warnings, all_wards):
        # Không phục hồi dấu tên đường/thôn khi chưa có từ điển chứng thực.
        for f in ("duong", "thon_xom"):
            name = detail[f].split(" ", 1)[-1] if detail[f] else ""
            if any(c.isalpha() for c in name) and bo_dau(name) == name.casefold():
                warnings.append("ten_chi_tiet_chua_xac_minh_dau")
        result = KetQua(**{f: detail[f] for f in FIELDS},
                        ma_xa=ma_xa, ma_tinh=ma_tinh,
                        xa_phuong=self.danh_muc.ten_day_du("moi", ma_xa) if ma_xa else "",
                        tinh=self.danh_muc.ten_day_du("moi", ma_tinh) if ma_tinh else "",
                        canh_bao=list(dict.fromkeys(warnings)),
                        phan_chua_phan_loai=detail["phan_chua_phan_loai"])
        result.dia_chi_chuan = _chuan_chuoi_dia_chi(result)
        if not ma_xa:
            result.xa_moi_ung_vien = [{"ma_xa": w, "ten": self.danh_muc.ten_day_du("moi", w),
                                       "ma_tinh": self.danh_muc.lay("moi", w).ma_cha} for w in sorted(all_wards)]
        return result

    def _dung_dau_vet(self, result, records, chuoi, best, spans, crf_context, name_evidence):
        for u in sorted(best.ung_vien, key=lambda u: u.bat_dau):
            result.dau_vet.append(_tao_dau_vet(records, chuoi, u.bat_dau, u.ket_thuc,
                                               truong=u.cap, ma=u.ma, moc=u.cay,
                                               kieu_khop=u.kieu_khop, diem=u.diem))
        for s in spans:
            result.dau_vet.append(_tao_dau_vet(records, chuoi, s["bat_dau"], s["ket_thuc"],
                                               truong=s["truong"], gia_tri=s["gia_tri"],
                                               kieu_khop="crf" if crf_context is not None else "luat"))
            if s['truong'] == 'duong' and name_evidence:
                result.dau_vet[-1]['chuan_hoa_ten'] = name_evidence

    def _dung_thong_ke(self, tokens, candidates, ranked, close, outcomes, score,
                       crf_context, name_evidence, result, records, chuoi):
        thong_ke = {"so_token": len(tokens), "so_ung_vien": len(candidates), "so_gia_thuyet": len(ranked),
                    "so_cach_hieu_gan_nhat": len(close), "so_ket_qua_dich_gan_nhat": len(outcomes), "diem": round(score, 4),
                    "moc_dich": "2025-07-01", "mo_hinh": "crf_va_diem_ghep_tay" if crf_context is not None else "luat_va_diem_tay"}
        if crf_context is not None:
            thong_ke['crf_model_sha256'] = self.bo_tach.ma_bam
            thong_ke['crf_bio_loi_truoc_sua'] = crf_context.loi_bio
        if hasattr(self.bo_tach, 'phien_ban'):
            thong_ke['mo_hinh'] = getattr(self.bo_tach, 'ten_mo_hinh', 'char_cnn_crf') + '_va_diem_tay'
            thong_ke['diem_nhan_dien'] = 'log_softmax_emission_khong_phai_marginal_CRF'
            thong_ke['tra_cuu_neural'] = crf_context.lookup_stats
            if hasattr(crf_context, 'segmentation_fallback'):
                thong_ke['tach_tu_fallback_raw'] = crf_context.segmentation_fallback
        if self.bo_xep_hang is not None:
            thong_ke['mo_hinh'] = getattr(self.bo_tach, 'ten_mo_hinh', 'char_cnn_crf') + '_va_lambdarank'
            thong_ke['ranker_sha256'] = self.bo_xep_hang.ma_bam
            thong_ke['diem_khong_phai_xac_suat'] = True
        thong_ke["phien_ban"] = self.PHIEN_BAN
        if self.tu_dien_duong is not None:
            thong_ke['tu_dien_duong_sha256'] = self.tu_dien_duong.ma_bam
            thong_ke['ten_duong_da_doi'] = bool(name_evidence)
        if self.hop_dong:
            from .hop_dong import bang_chung
            thong_ke['hop_dong'] = bang_chung(result, ranked, close, records, crf_context, self.danh_muc, self.tu_dien_duong, chuoi)
            if thong_ke['hop_dong']['truong']['duong']['ung_vien_ten']:
                result.canh_bao.append('ten_duong_chi_la_goi_y_chua_xac_minh')
        return thong_ke

    def chuan_hoa(self, chuoi: str) -> KetQua:
        records, candidates, crf_context, ranked = self.tao_gia_thuyet(chuoi)
        tokens = [t.chu for t in records]
        (score, best, detail, spans, unknown, inferred, close,
         outcomes, target_sets, ma_xa, ma_tinh, warnings, wards) = self._chon_gia_thuyet(
            tokens, candidates, crf_context, ranked
        )
        all_wards = set().union(*(w for w, _ in target_sets))
        self._xac_lap_canh_bao(
            warnings, wards, best, candidates, unknown, crf_context, inferred,
            detail, ma_xa, ma_tinh, chuoi
        )
        detail, spans, unknown, name_evidence = phuc_hoi_ten_duong(
            detail, spans, unknown, tokens, ma_tinh, self.tu_dien_duong, self.hop_dong,
            tien_to_mac_dinh=self.tien_to_mac_dinh,
            tien_to_duong=self.tien_to_duong,
            tien_to_so_nha=self.tien_to_so_nha
        )
        if name_evidence:
            warnings.append('ten_duong_tham_chieu_train_chua_xac_minh')
        else:
            detail, spans, bo_viet_tat = bo_duong_viet_tat_chua_giai(detail, spans, tokens, chuoi)
            if bo_viet_tat:
                warnings.append('ten_duong_viet_tat_chua_giai')
        result = self._dung_ket_qua(detail, ma_xa, ma_tinh, warnings, all_wards)
        self._dung_dau_vet(result, records, chuoi, best, spans, crf_context, name_evidence)
        result.thong_ke = self._dung_thong_ke(
            tokens, candidates, ranked, close, outcomes, score,
            crf_context, name_evidence, result, records, chuoi
        )
        return result
