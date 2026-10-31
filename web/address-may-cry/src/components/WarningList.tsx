import React from 'react';
import { IconAlertTriangle } from './Icons';
import { describeWarning } from '../lib/warnings';
import { readCandidate } from '../lib/kinds';
import './components.css';

export function WarningList({ codes }: { codes: string[] }) {
  if (!codes || codes.length === 0) return null;
  const unique = Array.from(new Set(codes));
  return (
    <section className="panel-block warn-block" aria-label="Cảnh báo">
      <h3 className="block-title">
        <IconAlertTriangle size={16} aria-hidden="true" /> Cần lưu ý ({unique.length})
      </h3>
      <ul className="warn-list">
        {unique.map((code) => {
          const info = describeWarning(code);
          return (
            <li key={code}>
              <strong>{info.label}</strong>
              <span>{info.desc}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function CandidateList({ items }: { items: Record<string, string>[] }) {
  if (!items || items.length === 0) return null;
  return (
    <section className="panel-block" aria-label="Xã/phường ứng viên">
      <h3 className="block-title">Xã/phường mới có thể đúng ({items.length})</h3>
      <p className="block-hint">Địa chỉ cũ có thể thuộc nhiều nơi sau 01/07/2025. Hãy chọn nơi đúng với thực tế.</p>
      <ul className="cand-list">
        {items.map((c, i) => {
          const r = readCandidate(c);
          return (
            <li key={i} className="cand-item">
              <span className="cand-name">{r.name || 'Không rõ tên'}</span>
              {(r.province || r.code || r.provinceCode) && (
                <span className="cand-meta">
                  {r.province && <>{r.province} · </>}
                  {r.code && <>Mã xã <code>{r.code}</code></>}
                  {r.provinceCode && <> · Mã tỉnh <code>{r.provinceCode}</code></>}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
