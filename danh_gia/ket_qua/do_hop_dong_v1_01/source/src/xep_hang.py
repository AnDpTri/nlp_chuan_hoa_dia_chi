"""LightGBM LambdaRank trên giả thuyết; không đưa mã địa phương vào feature."""

import hashlib
import json
from pathlib import Path

from .chuyen_doi import tap_dich
from .tach_phan_con import FIELDS

FEATURES = ['diem_tay', 'so_token', 'so_admin', 'bao_phu_admin', 'chua_hieu',
            'so_chi_tiet', 'bao_phu_chi_tiet', 'chi_tiet_suy_ra',
            'so_xa_dich', 'so_tinh_dich', 'tron_moc', 'co_tinh', 'co_huyen', 'co_xa',
            'co_so_nha', 'co_ngo', 'co_thon', 'co_duong',
            'admin_co_tien_to', 'khop_chinh_xac', 'khop_khong_dau', 'khop_viet_tat',
            'khop_sai_chinh_ta', 'khop_khac_dau', 'khop_khac_loai',
            'diem_vai_tro_admin', 'diem_O_admin', 'ung_vien_bo_qua_co_tien_to']


def dac_trung_gia_thuyet(item, tokens, candidates, dm, context):
    score, path, detail, spans, unknown, inferred = item
    used = {i for u in path.ung_vien for i in range(u.bat_dau, u.ket_thuc)}
    wards, provinces = tap_dich(path, dm)
    selected = path.ung_vien
    roles = sum(context.diem_ung_vien(u) for u in selected) if hasattr(context, 'diem_ung_vien') else 0.
    return [score, len(tokens), len(selected), len(used), len(unknown), len(spans),
            sum(s['ket_thuc'] - s['bat_dau'] for s in spans), int(inferred),
            len(wards), len(provinces), int(path.cay == 'tron'),
            *[int(any(u.cap == c for u in selected)) for c in ('tinh', 'huyen', 'xa')],
            *[int(bool(detail[f])) for f in FIELDS],
            sum(u.co_tien_to for u in selected),
            *[sum(u.kieu_khop == kind for u in selected) for kind in
              ('chinh_xac', 'khong_dau', 'viet_tat', 'sai_chinh_ta', 'khac_dau', 'khac_loai')],
            roles, context.diem_hanh_chinh(used) if context else 0.,
            len({(u.bat_dau, u.ket_thuc) for u in candidates if u.co_tien_to and not used.intersection(range(u.bat_dau, u.ket_thuc))})]


class BoXepHang:
    def __init__(self, model_path, extractor_sha256, catalogue_sha256):
        import lightgbm as lgb
        path = Path(model_path)
        meta = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        if meta['features'] != FEATURES or meta['extractor_sha256'] != extractor_sha256:
            raise ValueError('Ranker khác schema hoặc mô hình nhận diện lúc train')
        if meta['catalogue_sha256'] != catalogue_sha256:
            raise ValueError('Danh mục đã thay đổi so với lúc train ranker')
        self.model = lgb.Booster(model_file=str(path))
        self.ma_bam = hashlib.sha256(path.read_bytes()).hexdigest()
        self.nguong_gan = meta['close_margin']

    def cham_diem(self, features):
        import numpy as np
        return self.model.predict(np.asarray(features, dtype=np.float64), num_threads=1).tolist()
