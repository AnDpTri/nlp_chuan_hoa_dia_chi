"""Module Tiền xử lý: biến chuỗi bẩn thành DiaChiSach có cấu trúc.

Bao gồm tách token, nhận diện (CRF, CNN, Trie, ViDeBERTa), sinh và xếp hạng giả thuyết,
định dạng chi tiết và khôi phục tên đường. KHÔNG chuyển đổi mã hành chính mới.
"""

from ..danh_muc import DanhMuc
from ..kieu_du_lieu import DiaChiSach, DonViNhan, NoiBoTienXuLy
from .tim_kiem import dung_trie, sinh_ung_vien, bo_sung_tu_luoi_goc
from .tien_xu_ly import token_co_vi_tri, bo_dau
from .giai_ma import tim_duong_di
from .tach_phan_con import tach_co_dau_vet, FIELDS
from .quy_tac import cac_tien_to, CHI_TIET, khop_tien_to
from .phuc_hoi_duong import phuc_hoi_ten_duong, bo_duong_viet_tat_chua_giai


def _tao_dau_vet(records, chuoi, a, b, **extra):
    return {"token_bat_dau": a, "token_ket_thuc": b, "ky_tu_bat_dau": records[a].bat_dau,
            "ky_tu_ket_thuc": records[b-1].ket_thuc,
            "doan_goc": chuoi[records[a].bat_dau:records[b-1].ket_thuc], **extra}


def _don_vi_nhan(duong_di):
    """Rút giả thuyết beam về danh sách đơn vị sạch (cấp, mã, mốc), giữ thứ tự."""
    return [DonViNhan(cap=u.cap, ma=u.ma, cay=u.cay) for u in duong_di.ung_vien]


def token_hanh_chinh_kha_thi(records, candidates, crf_context, ma_tinh, dm):
    """Token mà CRF gán là đơn vị hành chính VÀ có ứng viên hành chính khả thi phủ nó
    (cùng tỉnh mới đã chọn; chưa chọn tỉnh thì cần khớp chính xác). Các token này không được dùng làm tên đường.
    Ví dụ 'Hà Nội' gán tỉnh, khớp đúng tỉnh 01 -> cấm; 'Hoàng Văn Thụ' gán xã nhưng không có xã đó trong tỉnh -> không cấm."""
    char_spans = getattr(crf_context, 'char_spans', None)
    if not char_spans:
        return frozenset()
    crf_hc = {i for i, t in enumerate(records)
              for r, a, b in char_spans if r in ('xa', 'huyen', 'tinh') and a <= t.bat_dau and t.ket_thuc <= b}
    cam = set()
    for u in candidates:
        # Khớp gần đúng (sai chính tả) là bằng chứng yếu: 'Trần' ~ 'Trà An' không đủ để cấm đoạn làm tên đường.
        if u.kieu_khop == 'sai_chinh_ta' or not crf_hc.intersection(range(u.bat_dau, u.ket_thuc)):
            continue
        kha_thi = ma_tinh in dm.dich_tinh(u.cay, u.ma) if ma_tinh else u.kieu_khop == 'chinh_xac'
        if kha_thi:
            cam.update(i for i in range(u.bat_dau, u.ket_thuc) if i in crf_hc)
    return frozenset(cam)


def dau_vet_hanh_chinh_khong_khop(records, chuoi, crf_context, candidates, unknown):
    """Đoạn CRF gán là xã/huyện/tỉnh mà vẫn nằm trong phần chưa phân loại: ghi dấu vết với ma rỗng và lý do,
    để đầu ra không coi nó là chữ thừa. 'khong_co_trong_danh_muc' khi không có ứng viên nào trên đoạn,
    'khong_khop_dia_ban' khi có đơn vị cùng tên nhưng không hợp với các đơn vị còn lại."""
    out = []
    con_lai = set(unknown)
    for r, a, b in getattr(crf_context, 'char_spans', None) or ():
        if r not in ('xa', 'huyen', 'tinh'):
            continue
        idx = [i for i, t in enumerate(records) if a <= t.bat_dau and t.ket_thuc <= b and i in con_lai]
        if not idx:
            continue
        lo, hi = idx[0], idx[-1] + 1
        co_ung_vien = any(u.bat_dau < hi and lo < u.ket_thuc for u in candidates)
        out.append(_tao_dau_vet(records, chuoi, lo, hi, truong=r, ma='', moc='',
                                kieu_khop='khong_khop_dia_ban' if co_ung_vien else 'khong_co_trong_danh_muc'))
    return out


def _tinh_cua_duong_di(duong_di, dm):
    provinces = None
    for u in duong_di.ung_vien:
        ps = set(dm.dich_tinh(u.cay, u.ma))
        provinces = ps if provinces is None else provinces & ps
    return set() if provinces is None else provinces


class BoLamSach:
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

    def _sinh_ung_vien_va_mo_rong(self, records, lexical_records, tokens, crf_context):
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
            from .crf_chi_tiet import bio_spans
            protected = []
            for field, a, b in bio_spans(crf_context.labels)[0]:
                marker = khop_tien_to(tokens[a:b], 0, CHI_TIET)
                if field == 'duong' and marker and marker[1][0] == 'duong':
                    protected.append((a + marker[0], b))
            candidates = [u for u in candidates if u.co_tien_to or not any(
                a <= u.bat_dau and u.ket_thuc <= b for a, b in protected)]
        return candidates, crf_context

    def tao_gia_thuyet(self, chuoi):
        if not isinstance(chuoi, str):
            raise TypeError("Địa chỉ phải là chuỗi")
        records = token_co_vi_tri(chuoi)
        lexical_records = records
        crf_context = self.bo_tach.chuan_bi_chuoi(chuoi) if hasattr(self.bo_tach, 'chuan_bi_chuoi') else None
        if crf_context is not None:
            records = crf_context.records
        tokens = [t.chu for t in records]
        candidates, crf_context = self._sinh_ung_vien_va_mo_rong(records, lexical_records, tokens, crf_context)
        admin_spans = {(u.bat_dau, u.ket_thuc) for u in candidates if u.co_tien_to and u.kieu_khop != "sai_chinh_ta"}
        prefixes = {i: p for i, p in cac_tien_to(tokens).items() if not any(a < i < b for a, b in admin_spans)}
        paths = tim_duong_di(candidates, len(tokens), self.danh_muc, self.beam)
        ranked = []
        for path in paths:
            occupied = {i for u in path.ung_vien for i in range(u.bat_dau, u.ket_thuc)}
            detail, spans, unknown, inferred = (
                crf_context.tach(occupied, tien_to_mac_dinh=self.tien_to_mac_dinh,
                                 tien_to_so_nha=self.tien_to_so_nha, tien_to_duong=self.tien_to_duong)
                if crf_context is not None
                else tach_co_dau_vet(tokens, occupied, prefixes, tien_to_mac_dinh=self.tien_to_mac_dinh,
                                     tien_to_so_nha=self.tien_to_so_nha, tien_to_duong=self.tien_to_duong))
            score = path.diem - .12*len(unknown) + .05*sum(s["ket_thuc"]-s["bat_dau"] for s in spans)
            if crf_context is not None:
                score += crf_context.diem_hanh_chinh(occupied)
                if hasattr(crf_context, 'diem_ung_vien'):
                    score += sum(crf_context.diem_ung_vien(u) for u in path.ung_vien)
            ranked.append((score, path, detail, spans, unknown, inferred))
        return records, candidates, crf_context, ranked

    def _chon_gia_thuyet_va_tinh(self, tokens, candidates, crf_context, ranked):
        if self.bo_xep_hang is not None:
            from .xep_hang import dac_trung_gia_thuyet
            features = [dac_trung_gia_thuyet(x, tokens, candidates, self.danh_muc, crf_context) for x in ranked]
            scores = self.bo_xep_hang.cham_diem(features)
            ranked = [(float(s), *item[1:]) for s, item in zip(scores, ranked)]
        ranked.sort(key=lambda x: -x[0])
        score, best, detail, spans, unknown, inferred = ranked[0]
        margin = self.bo_xep_hang.nguong_gan if self.bo_xep_hang is not None else .65
        close = [x for x in ranked if score - x[0] <= margin]
        # Tên hiện hành thắng tên cũ khi điểm gần bằng: tên cũ chỉ dùng khi không còn cách hiểu nào bằng tên hiện hành.
        hien_hanh = [x for x in close if not any(u.ten_cu for u in x[1].ung_vien)]
        if hien_hanh and len(hien_hanh) < len(close):
            close = hien_hanh
            score, best, detail, spans, unknown, inferred = close[0]
        provinces_sets = [_tinh_cua_duong_di(x[1], self.danh_muc) for x in close]
        positive_provinces = set().union(*provinces_sets)
        ma_tinh = next(iter(positive_provinces)) if len(positive_provinces) == 1 else ""
        return score, best, detail, spans, unknown, inferred, close, ranked, ma_tinh

    def _xu_ly_duong_va_canh_bao(self, detail, spans, unknown, tokens, ma_tinh, chuoi, cam=frozenset()):
        detail, spans, unknown, name_evidence = phuc_hoi_ten_duong(
            detail, spans, unknown, tokens, ma_tinh, self.tu_dien_duong, self.hop_dong,
            tien_to_mac_dinh=self.tien_to_mac_dinh,
            tien_to_duong=self.tien_to_duong,
            tien_to_so_nha=self.tien_to_so_nha,
            cam=cam
        )
        road_warnings = []
        if name_evidence:
            road_warnings.append('ten_duong_tham_chieu_train_chua_xac_minh')
        else:
            detail, spans, bo_viet_tat = bo_duong_viet_tat_chua_giai(detail, spans, tokens, chuoi)
            if bo_viet_tat:
                road_warnings.append('ten_duong_viet_tat_chua_giai')
        for f in ("duong", "thon_xom"):
            name = detail[f].split(" ", 1)[-1] if detail[f] else ""
            if any(c.isalpha() for c in name) and bo_dau(name) == name.casefold():
                road_warnings.append("ten_chi_tiet_chua_xac_minh_dau")
        return detail, spans, unknown, name_evidence, road_warnings

    def _thu_thap_canh_bao_giua(self, best, candidates, unknown, crf_context, inferred, detail):
        warnings = []
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
        return warnings

    def _tao_dau_vet_va_thong_ke(self, records, chuoi, best, spans, crf_context, name_evidence, tokens, candidates, ranked, close, score):
        dau_vet = []
        for u in sorted(best.ung_vien, key=lambda u: u.bat_dau):
            dau_vet.append(_tao_dau_vet(records, chuoi, u.bat_dau, u.ket_thuc,
                                        truong=u.cap, ma=u.ma, moc=u.cay,
                                        kieu_khop=u.kieu_khop, diem=u.diem))
        for s in spans:
            dau_vet.append(_tao_dau_vet(records, chuoi, s["bat_dau"], s["ket_thuc"],
                                        truong=s["truong"], gia_tri=s["gia_tri"],
                                        kieu_khop="crf" if crf_context is not None else "luat"))
            if s['truong'] == 'duong' and name_evidence:
                dau_vet[-1]['chuan_hoa_ten'] = name_evidence
        thong_ke = {"so_token": len(tokens), "so_ung_vien": len(candidates), "so_gia_thuyet": len(ranked),
                    "so_cach_hieu_gan_nhat": len(close), "diem": round(score, 4),
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
        return dau_vet, thong_ke

    def lam_sach(self, chuoi: str) -> DiaChiSach:
        return self.lam_sach_chi_tiet(chuoi)[0]

    def lam_sach_chi_tiet(self, chuoi: str) -> tuple[DiaChiSach, NoiBoTienXuLy]:
        records, candidates, crf_context, ranked = self.tao_gia_thuyet(chuoi)
        tokens = [t.chu for t in records]
        score, best, detail, spans, unknown, inferred, close, ranked, ma_tinh = self._chon_gia_thuyet_va_tinh(
            tokens, candidates, crf_context, ranked
        )
        mid_warnings = self._thu_thap_canh_bao_giua(best, candidates, unknown, crf_context, inferred, detail)
        detail_truoc_duong = dict(detail)
        cam = token_hanh_chinh_kha_thi(records, candidates, crf_context, ma_tinh, self.danh_muc)
        detail, spans, unknown, name_evidence, road_warnings = self._xu_ly_duong_va_canh_bao(
            detail, spans, unknown, tokens, ma_tinh, chuoi, cam
        )
        if not unknown:  # bước khôi phục đường đã xếp hết phần chưa phân loại
            mid_warnings = [w for w in mid_warnings if w != "phan_chua_phan_loai"]
        post_warnings = (["dau_vao_rong"] if not chuoi.strip() else []) + road_warnings
        dau_vet, thong_ke = self._tao_dau_vet_va_thong_ke(
            records, chuoi, best, spans, crf_context, name_evidence, tokens, candidates, ranked, close, score
        )
        dau_vet += dau_vet_hanh_chinh_khong_khop(records, chuoi, crf_context, candidates, unknown)
        don_vi_xa = next((u for u in best.ung_vien if u.cap == "xa"), None)
        don_vi_huyen = next((u for u in best.ung_vien if u.cap == "huyen"), None)
        don_vi_tinh = next((u for u in best.ung_vien if u.cap == "tinh"), None)
        dm = self.danh_muc
        sach = DiaChiSach(
            so_nha=detail["so_nha"],
            ngo_ngach_hem=detail["ngo_ngach_hem"],
            thon_xom=detail["thon_xom"],
            duong=detail["duong"],
            phan_chua_phan_loai=detail["phan_chua_phan_loai"],
            don_vi=_don_vi_nhan(best),
            cach_hieu_gan=[_don_vi_nhan(x[1]) for x in close],
            ma_xa=don_vi_xa.ma if don_vi_xa else "",
            ma_huyen=don_vi_huyen.ma if don_vi_huyen else "",
            ma_tinh=don_vi_tinh.ma if don_vi_tinh else "",
            xa=dm.ten_day_du(don_vi_xa.cay, don_vi_xa.ma) if don_vi_xa else "",
            huyen=dm.ten_day_du(don_vi_huyen.cay, don_vi_huyen.ma) if don_vi_huyen else "",
            tinh=dm.ten_day_du(don_vi_tinh.cay, don_vi_tinh.ma) if don_vi_tinh else "",
            cay=best.cay,
            canh_bao_giua=mid_warnings,
            canh_bao_sau=post_warnings,
            canh_bao=mid_warnings + post_warnings,
            dau_vet=dau_vet,
            thong_ke=thong_ke,
            chuoi=chuoi,
        )
        noi_bo = NoiBoTienXuLy(records=records, candidates=candidates, crf_context=crf_context, ranked=ranked,
                               close=close, score=score, spans=spans, name_evidence=name_evidence,
                               chi_tiet_truoc_duong=detail_truoc_duong)
        return sach, noi_bo
