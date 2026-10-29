"""Bằng chứng độc lập với điểm model: quan sát, định dạng, giải nghĩa.

Không dùng threshold mới, không đọc dữ liệu train/dev và không chọn đáp án.
Tên từ train là gợi ý; danh mục hành chính không chứng thực tên đường.
"""

from .chuyen_doi import sang_cay_moi
from .tach_phan_con import FIELDS
from .crf_chi_tiet import tien_to_hien_thi
from .quy_tac import CHI_TIET, khop_tien_to


def bang_chung(result, ranked, close, records, context, dm, names, raw):
    fields = {}
    for field in FIELDS:
        observed = [s for s in result.dau_vet if s['truong'] == field]
        operations = []
        for span in observed:
            tokens = [t.chu for t in records[span['token_bat_dau']:span['token_ket_thuc']]]
            direct = khop_tien_to(tokens, 0, CHI_TIET) if tokens else None
            display = tien_to_hien_thi(tokens, field)
            if display and (not direct or direct[1][0] != field):
                kind = 'giai_nghia_tien_to_telex'
            elif field == 'duong' and not display:
                kind = 'gan_loai_duong_tu_vai_tro'
            elif field == 'duong' and direct and direct[1][1] == 'Đường' and not span['gia_tri'].startswith('Đường '):
                kind = 'giai_nghia_loai_tuyen_long'
            else:
                kind = 'dinh_dang_vai_tro'
            operations.append({'loai': kind, 'doan_goc': span['doan_goc'],
                               'start': span['ky_tu_bat_dau'], 'end': span['ky_tu_ket_thuc'],
                               'gia_tri': span['gia_tri'],
                               'gia_thuyet_giu_chu_goc': span['doan_goc']})
        candidates = names.ung_vien(result.duong, result.ma_tinh) if names and field == 'duong' else []
        value = getattr(result, field)
        state = ('co_goi_y_chua_xac_minh' if candidates else
                 'co_quan_sat_chua_xac_minh_ten' if value and field in ('duong', 'thon_xom') else
                 'dinh_dang_theo_vai_tro' if value else 'khong_co_gia_tri')
        fields[field] = {'gia_tri': value, 'trang_thai': state,
                         'thao_tac': operations, 'ung_vien_ten': candidates}
    hypotheses = []
    all_hypotheses = []
    for item in ranked:
        score, path, detail, spans, unknown, inferred = item
        w, p, warnings = sang_cay_moi(path, detail, dm)
        hypothesis = {'diem_khong_phai_xac_suat': float(score),
                           'chi_tiet': {f: detail[f] for f in FIELDS}, 'ma_xa': w, 'ma_tinh': p,
                           'canh_bao': warnings,
                           'nguon_hanh_chinh': [{'moc': u.cay, 'ma': u.ma, 'cap': u.cap,
                                                'kieu_khop': u.kieu_khop,
                                                'start': records[u.bat_dau].bat_dau,
                                                'end': records[u.ket_thuc-1].ket_thuc} for u in path.ung_vien]}
        all_hypotheses.append(hypothesis)
        if any(item is x for x in close):
            hypotheses.append(hypothesis)
    for field in ('ma_xa', 'ma_tinh'):
        values = sorted({h[field] for h in hypotheses})
        state = 'co_doi_chieu_danh_muc' if getattr(result, field) else ('nhieu_cach_hieu_hoac_chia' if len(values) > 1 else 'chua_xac_dinh')
        fields[field] = {'gia_tri': getattr(result, field), 'trang_thai': state,
                         'gia_tri_o_cac_nhanh_gan': values,
                         'nguon': [s for s in result.dau_vet if s['truong'] in ('xa', 'huyen', 'tinh')]}
    # Chỉ ghi xung đột quan sát/model; không tự loại ứng viên vì span model.
    conflicts = []
    observations = []
    without_admin = None
    if context is not None:
        from .crf_chi_tiet import bio_spans
        detail_spans = bio_spans(context.labels)[0]
        for field, a, b in detail_spans:
            lo, hi = records[a].bat_dau, records[b-1].ket_thuc
            observations.append({'truong': field, 'start': lo, 'end': hi, 'doan_goc': raw[lo:hi]})
        without_admin = context.tach(set())[0]
        for _, path, *_ in ranked:
            for u in path.ung_vien:
                for field, a, b in detail_spans:
                    if max(a, u.bat_dau) < min(b, u.ket_thuc):
                        conflict = {'truong_model': field, 'moc': u.cay, 'ma': u.ma,
                                    'start': records[u.bat_dau].bat_dau, 'end': records[u.ket_thuc-1].ket_thuc}
                        if conflict not in conflicts:
                            conflicts.append(conflict)
    return {'phien_ban': 1, 'chinh_sach': 'train_chi_goi_y_khong_tu_dien_ten_chac_chan',
            'truong': fields, 'gia_thuyet_gan': hypotheses,
            'gia_thuyet_da_xet': all_hypotheses,
            'quan_sat_model_truoc_ghep': observations,
            'chi_tiet_khi_khong_chon_hanh_chinh': without_admin,
            'so_gia_thuyet_da_xet': len(ranked), 'xung_dot_model_hanh_chinh': conflicts,
            'gioi_han': 'Beam hữu hạn, điểm/ngưỡng gần chưa hiệu chỉnh; provenance không chứng minh nhãn đúng ngữ nghĩa.'}
