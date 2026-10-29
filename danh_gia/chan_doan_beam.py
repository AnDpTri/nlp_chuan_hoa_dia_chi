"""Chỉ tái chạy các câu sai dev khó để xuất beam và phân loại có bằng chứng."""
import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from src.char_cnn import BoTachCharCNN
from src.videberta import BoTachViDeberta
from src.chuan_hoa import BoChuanHoa
from src.chuan_ten_duong import TuDienDuong, tach_ten, cac_dang, khoa
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.xep_hang import BoXepHang
from src.tien_xu_ly import bo_dau
from .chay_ban_thu import ROOT, CORE, norm, digest
from .du_lieu_crf import doc_jsonl, ghi_jsonl


class Capture(BoChuanHoa):
    def tao_gia_thuyet(self, text):
        self.last = super().tao_gia_thuyet(text)
        return self.last


def same(p, r, fields=CORE, transform=norm):
    return all(transform(p[f]) == transform(r[f]) for f in fields)


def detail_subgroup(row):
    a, b = row['nearest']['six_fields']['duong'], row['reference']['duong']
    pa, pb = tach_ten(a), tach_ten(b)
    if not b and a: return 'reference_duong_trong_can_ra_soat'
    if pa and pb and khoa(pa[1]) == khoa(pb[1]) and pa[0] != pb[0]: return 'khac_loai_duong'
    if pa and pb and khoa(pa[1]) in cac_dang(pb[1]): return 'ten_viet_tat_hoac_dinh_dang'
    if pa and pb and khoa(pa[1]).endswith(khoa(pb[1])) and khoa(pa[1]) != khoa(pb[1]):
        return 'thua_chu_dau_ten_co_the_tien_to_loi'
    if 'span_chi_tiet_goc_khong_khop' in row['tags']: return 'model_span_khong_khop'
    return 'noi_dung_chi_tiet_khac_can_ra_soat'


def run():
    matrix = ROOT / 'danh_gia/ket_qua/ma_tran_v1_01'
    output = ROOT / 'danh_gia/ket_qua/chan_doan_beam_v1_01'
    output.mkdir(parents=True, exist_ok=False)
    cnn = ROOT / 'mo_hinh/thu_nghiem/char_v1_01'
    vi = ROOT / 'mo_hinh/thu_nghiem/videberta_v1_01'
    dm = DanhMuc(cnn / 'snapshot/clean')
    names = TuDienDuong(ROOT / 'danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json')
    gold = {r['id']: r for r in doc_jsonl(cnn / 'data/dev_kho.jsonl')}
    plain = lambda s: bo_dau(norm(s))
    compact = lambda s: ''.join(c for c in plain(s) if c.isalnum())
    report = {'scope': 'Chẩn đoán các câu chưa khớp dev khó. Không đổi nhãn/model, không dùng test cuối.',
              'category_warning': 'Phân loại cơ học theo reference yếu, không xác nhận nhãn đúng ngữ nghĩa. Các nhãn cần rà chỉ là nghi vấn.',
              'methods': {}}
    for method, backend, run_dir, original in [
        ('cnn', BoTachCharCNN(cnn / 'char_cnn.pt'), cnn, 'cnn_ranker_sua'),
        ('videberta', BoTachViDeberta(vi / 'model'), vi, 'videberta_tay_sua')]:
        ranker = BoXepHang(run_dir / 'ranker.txt', backend.ma_bam, dm.ma_bam) if method == 'cnn' else None
        model = Capture(danh_muc=dm, bo_tach=backend, bo_xep_hang=ranker,
                        tu_dien_duong=names, bao_ve_duong=True)
        rows = [r for r in doc_jsonl(matrix / f'{original}_dev_kho.jsonl') if not same(r['prediction'], r['reference'])]
        counts, tags = Counter(), Counter()
        results = []
        for i, row in enumerate(rows):
            r = row['reference']
            result = asdict(model.chuan_hoa(row['input']))
            assert same(result, row['prediction']), row['id']
            records, candidates, context, items = model.last
            beam = []
            for score, path, detail, spans, unknown, inferred in items:
                w, p, warnings = sang_cay_moi(path, detail, dm)
                detail = dict(detail)
                detail['duong'] = names.chuan_hoa(detail['duong'], p)[0]
                pred = {f: detail[f] for f in CORE[:4]}
                pred.update(ma_xa=w, ma_tinh=p)
                beam.append({'six_fields': pred, 'hand_score': score,
                             'mismatch_fields': [f for f in CORE if norm(pred[f]) != norm(r[f])],
                             'source_admin': [asdict(u) for u in path.ung_vien], 'detail_spans': spans})
            full = any(same(b['six_fields'], r) for b in beam)
            admin = any(same(b['six_fields'], r, CORE[4:]) for b in beam)
            detail = any(same(b['six_fields'], r, CORE[:4]) for b in beam)
            if full: category = 'co_dap_an_trong_beam_nhung_output_chua_khop'
            elif any(same(b['six_fields'], r, transform=plain) for b in beam): category = 'chi_thieu_phuc_hoi_dau'
            elif any(same(b['six_fields'], r, transform=compact) for b in beam): category = 'khac_dau_khoang_trang_dau_cau'
            elif detail and not admin: category = 'chi_thieu_phuong_an_hanh_chinh'
            elif detail and admin: category = 'chi_tiet_va_hanh_chinh_dung_o_hai_nhanh_khac_nhau'
            elif not admin: category = 'thieu_ca_hanh_chinh_va_chi_tiet'
            else: category = 'co_hanh_chinh_dung_nhung_chi_tiet_chua_khop'
            counts[category] += 1
            nearest = min(beam, key=lambda b: (len(b['mismatch_fields']), sum(abs(len(compact(b['six_fields'][f]))-len(compact(r[f]))) for f in CORE)))
            row_tags = []
            for f in nearest['mismatch_fields']:
                if not r[f] and nearest['six_fields'][f]: row_tags.append('reference_trong_' + f)
                elif r[f] and not nearest['six_fields'][f]: row_tags.append('output_thieu_' + f)
                else: row_tags.append('gia_tri_khac_' + f)
            gold_spans = {tuple(s) for s in gold[row['id']]['detail_spans_raw']}
            predicted_spans = {s for s in context.char_spans if s[0] in CORE[:4]}
            raw_exact = gold_spans == predicted_spans
            row_tags.append('span_chi_tiet_goc_khop' if raw_exact else 'span_chi_tiet_goc_khong_khop')
            if not full and raw_exact: row_tags.append('span_khop_nhung_output_chuan_hoa_chua_du')
            if not r['duong'] and result['duong']: row_tags.append('can_ra_soat_reference_duong_trong')
            tags.update(row_tags)
            results.append({'id': row['id'], 'input': row['input'], 'reference': r, 'output': result,
                            'category': category, 'tags': row_tags,
                            'reference_detail_spans': sorted(gold_spans), 'model_detail_spans': sorted(predicted_spans),
                            'beam_has_reference_admin': admin, 'beam_has_reference_detail': detail,
                            'beam_has_reference_six_fields': full, 'nearest': nearest, 'beam': beam})
            if (i+1) % 50 == 0: print(method, i+1, '/', len(rows), flush=True)
        subgroups = Counter()
        for row in results:
            if row['category'] == 'co_hanh_chinh_dung_nhung_chi_tiet_chua_khop':
                row['detail_subgroup'] = detail_subgroup(row)
                subgroups[row['detail_subgroup']] += 1
        report['methods'][method] = {'wrong_output': len(rows), 'beam_missing_reference': len(rows)-counts['co_dap_an_trong_beam_nhung_output_chua_khop'],
                                      'detail_subgroups_heuristic': dict(subgroups),
                                      'categories_exclusive': dict(counts), 'tags_overlapping': dict(tags)}
        ghi_jsonl(output / f'{method}_tung_cau.jsonl', results)
        print(json.dumps(report['methods'][method], ensure_ascii=False), flush=True)
        (output / 'thong_ke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Chẩn đoán câu sai dev khó', '', report['scope'], '', report['category_warning'], '',
             '| Nhóm loại trừ nhau | CNN ranker | ViDeBERTa điểm tay |', '|---|---:|---:|']
    categories = set().union(*(m['categories_exclusive'] for m in report['methods'].values()))
    for c in sorted(categories):
        lines.append('| '+c+' | '+' | '.join(str(report['methods'][m]['categories_exclusive'].get(c,0)) for m in ('cnn','videberta'))+' |')
    lines += ['', 'Mỗi JSONL chứa input/reference/output, span gốc, phương án gần nhất và toàn bộ beam. Nhánh gần nhất được chọn hậu kiểm bằng reference, không phải output triển khai.', '']
    (output / 'BAO_CAO.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    run()
