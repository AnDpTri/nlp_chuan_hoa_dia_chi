"""Đọc nhật ký chạy thử Address May Cry: những câu người dùng báo sai, lỗi xử lý, và câu có cảnh báo đáng ngờ.
Dùng: doc_log.py [thu_muc_log]   (mặc định web/address-may-cry/api/logs)
      doc_log.py --tat-ca        in thêm mọi lần chuẩn hóa"""
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
import collections, json, sys
from pathlib import Path

LOG = dd.LOG_WEB
F = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'xa_phuong', 'ma_xa', 'tinh', 'ma_tinh')
NGHI = {'thieu_xa', 'thieu_tinh', 'nhieu_cach_hieu', 'mau_thuan_hanh_chinh', 'phan_chua_phan_loai', 'xa_bi_chia'}


def tom_tat(r):
    res = r.get('result') or {}
    dong = '  ' + ' | '.join(f'{f}={res.get(f)!r}' for f in F if res.get(f))
    cb = res.get('canh_bao') or []
    if cb:
        dong += '\n  canh_bao: ' + ', '.join(cb)
    if res.get('phan_chua_phan_loai'):
        dong += f"\n  chua_phan_loai: {res['phan_chua_phan_loai']!r}"
    tp = res.get('thanh_phan') or []
    if tp:
        dong += '\n  thanh_phan: ' + ' / '.join(f"[{t.get('doan_goc')}]->{t.get('nhan_la')}" for t in tp)
    return dong + chan_doan(r.get('chan_doan'))


def chan_doan(cd):
    """Các bước trung gian: CRF gán gì, ứng viên mỗi đoạn, giả thuyết đầu, khôi phục đường, chuyển đổi."""
    if not cd:
        return '\n  (không có chẩn đoán: log ghi trước khi bật hoặc AMC_LOG≠1)'
    tx, cv = cd['tien_xu_ly'], cd['chuyen_doi']
    d = ['\n  -- chẩn đoán --', '  CRF: ' + ' / '.join(f"[{c['doan']}]->{c['truong']}" for c in tx['crf'])]
    for nhom in tx['ung_vien']:
        top = '; '.join(f"{u['ten']} {u['ma']}({u['cay']},{u['kieu_khop']},{u['diem']})" for u in nhom['top'][:4])
        d.append(f"  ứng viên [{nhom['doan']}] x{nhom['so_ung_vien']}: {top}")
    d.append(f"  giả thuyết: {tx['so_gia_thuyet']} (gần bằng: {tx['so_gia_thuyet_gan']})")
    for g in tx['gia_thuyet'][:3]:
        dv = ', '.join(f"{u['cap']}={u['ten']} {u['ma']}/{u['cay']}" for u in g['don_vi'])
        d.append(f"    {g['diem']:+.3f} [{dv}] chưa phân loại={g['chua_phan_loai']!r}")
    if tx['khoi_phuc_duong']:
        d.append('  khôi phục đường: ' + '; '.join(f"{k}: {v['truoc']!r} -> {v['sau']!r}" for k, v in tx['khoi_phuc_duong'].items()))
    for c in cv:
        d.append(f"  chuyển đổi {c['don_vi']} -> xã mới {c['xa_moi']} tỉnh mới {c['tinh_moi']}")
    return '\n'.join(d)


def main(thu_muc, tat_ca):
    rows = [json.loads(l) for p in sorted(Path(thu_muc).glob('phien_*.jsonl')) for l in open(p, encoding='utf-8') if l.strip()]
    rows = [r for r in rows if 'THU_NGHIEM_CLAUDE' not in (r.get('ghi_chu') or '') + (r.get('input') or '')]
    theo_id = {r['log_id']: r for r in rows}
    dem = collections.Counter(r['loai'] for r in rows)
    print('Tổng:', dict(dem))
    print('\n=== NGƯỜI DÙNG BÁO SAI ===')
    for r in (x for x in rows if x['loai'] == 'bao_sai'):
        print(f"- [{r['thoi_gian']}] {r['input']}\n  ghi chú: {r.get('ghi_chu') or '(trống)'}")
        goc = theo_id.get(r.get('ref_log_id'))
        if goc:
            print(tom_tat(goc))
    print('\n=== LỖI XỬ LÝ ===')
    for r in (x for x in rows if x['loai'] == 'loi_xu_ly'):
        print(f"- {r['input']}\n  {r['loi']}")
    print('\n=== CÓ CẢNH BÁO ĐÁNG NGỜ (chưa ai báo) ===')
    da_bao = {x.get('ref_log_id') for x in rows if x['loai'] == 'bao_sai'}
    for r in (x for x in rows if x['loai'] == 'chuan_hoa' and x['log_id'] not in da_bao):
        cb = set((r.get('result') or {}).get('canh_bao') or [])
        if tat_ca or cb & NGHI:
            print(f"- {r['input']}\n{tom_tat(r)}")


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args[0] if args else LOG, '--tat-ca' in sys.argv)
