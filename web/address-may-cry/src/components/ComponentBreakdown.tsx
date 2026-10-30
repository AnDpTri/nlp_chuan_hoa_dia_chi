import React from 'react';
import type { ThanhPhan, NhanThanhPhan } from '../shared/contracts';
import { KIND_LABEL, KIND_SHORT, KIND_ORDER, kindOf } from '../lib/kinds';
import './components.css';

export interface ComponentBreakdownProps {
  rawAddress: string;
  thanhPhan?: ThanhPhan[];
}

interface Segment {
  text: string;
  tp?: ThanhPhan;
}

function buildSegments(raw: string, list: ThanhPhan[]): Segment[] {
  const segs: Segment[] = [];
  let cursor = 0;
  const sorted = [...list].sort((a, b) => a.bat_dau - b.bat_dau);
  for (const tp of sorted) {
    if (tp.bat_dau < cursor) continue; // bỏ đoạn chồng lấn để không lặp chữ
    if (tp.bat_dau > cursor) segs.push({ text: raw.slice(cursor, tp.bat_dau) });
    segs.push({ text: tp.doan_goc || raw.slice(tp.bat_dau, tp.ket_thuc), tp });
    cursor = tp.ket_thuc;
  }
  if (cursor < raw.length) segs.push({ text: raw.slice(cursor) });
  return segs;
}

function MatchBadge({ value }: { value: ThanhPhan['doi_chieu'] }) {
  if (value === 'co') return <span className="badge badge-ok">Có đối chiếu</span>;
  if (value === 'khong') return <span className="badge badge-warning">Không đối chiếu</span>;
  return <span className="badge badge-neutral">Không xét</span>;
}

function KindTag({ kind }: { kind: NhanThanhPhan }) {
  return <span className="kind-tag" data-kind={kind}>{KIND_LABEL[kind]}</span>;
}

export const ComponentBreakdown: React.FC<ComponentBreakdownProps> = ({ rawAddress, thanhPhan = [] }) => {
  if (!thanhPhan || thanhPhan.length === 0) return null;
  const segments = buildSegments(rawAddress, thanhPhan);
  const used = new Set(thanhPhan.map((t) => kindOf(t.nhan_la)));
  const legend = KIND_ORDER.filter((k) => used.has(k));

  return (
    <div className="breakdown">
      <section className="panel-block" aria-label="Chuỗi nhập tô màu theo thành phần">
        <h3 className="block-title">Địa chỉ đã nhập, tô màu theo từng thành phần</h3>
        <p className="hl-string" lang="vi">
          {segments.map((seg, i) => {
            if (!seg.tp) return <span key={i} className="hl-gap">{seg.text}</span>;
            const kind = kindOf(seg.tp.nhan_la);
            return (
              <mark key={i} className="hl-chip" data-kind={kind}>
                <span className="hl-text">{seg.text}</span>
                <span className="hl-cap">{KIND_SHORT[kind]}</span>
              </mark>
            );
          })}
        </p>
        <ul className="legend" aria-label="Chú thích màu">
          {legend.map((k) => (
            <li key={k}><KindTag kind={k} /></li>
          ))}
        </ul>
      </section>

      <section className="panel-block table-block" aria-label="Bảng từng thành phần">
        <div className="block-head">
          <h3 className="block-title">Từng thành phần ({thanhPhan.length})</h3>
          <span className="block-hint">Mốc hành chính 01/07/2025</span>
        </div>
        <table className="comp-table">
          <thead>
            <tr>
              <th scope="col">Chữ trong địa chỉ</th>
              <th scope="col">Nhận là</th>
              <th scope="col">Chuẩn hóa</th>
              <th scope="col">Đối chiếu</th>
              <th scope="col">Kết quả mới</th>
            </tr>
          </thead>
          <tbody>
            {thanhPhan.map((item, idx) => {
              const kind = kindOf(item.nhan_la);
              const skip = kind === 'bo_qua';
              return (
                <tr key={idx} className={skip ? 'is-skip' : ''}>
                  <td data-label="Chữ trong địa chỉ"><span className="cell-raw">{item.doan_goc}</span></td>
                  <td data-label="Nhận là"><KindTag kind={kind} /></td>
                  <td data-label="Chuẩn hóa">{item.chuan_hoa || <span className="cell-none">—</span>}</td>
                  <td data-label="Đối chiếu">
                    <MatchBadge value={item.doi_chieu} />
                    {item.ly_do && <span className="cell-reason">{item.ly_do}</span>}
                  </td>
                  <td data-label="Kết quả mới">
                    {item.ket_qua_moi
                      ? <strong className={kind === 'huyen' ? 'cell-dim' : 'cell-new'}>{item.ket_qua_moi}</strong>
                      : <span className="cell-none">{skip ? '—' : 'Chưa xác định'}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
};
