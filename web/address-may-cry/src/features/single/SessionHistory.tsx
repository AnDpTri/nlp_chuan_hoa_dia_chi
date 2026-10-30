import React from 'react';
import type { NormalizeResponse } from '../../shared/contracts';

export interface HistoryItem {
  timestamp: number;
  input: string;
  response: NormalizeResponse;
}

const timeFmt = new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

interface Props {
  items: HistoryItem[];
  onPick: (item: HistoryItem) => void;
  onClear: () => void;
}

/** Lịch sử chỉ lưu trong bộ nhớ của phiên làm việc, không ghi vào localStorage. */
export function SessionHistory({ items, onPick, onClear }: Props) {
  if (items.length === 0) return null;
  return (
    <details className="card history-card">
      <summary>Lịch sử phiên này ({items.length})</summary>
      <div className="history-body">
        <p className="muted-note">Chỉ lưu tạm trong trang này, tải lại trang sẽ mất.</p>
        <ul className="history-list">
          {items.map((it) => (
            <li key={it.timestamp}>
              <button type="button" className="history-btn" onClick={() => onPick(it)}>
                <span className="history-meta">
                  {timeFmt.format(it.timestamp)} · {it.response.elapsed_ms}&nbsp;ms ·{' '}
                  {it.response.status === 'needs_review' ? 'Cần xem lại' : 'Đã xử lý'}
                </span>
                <span className="history-input">{it.input}</span>
              </button>
            </li>
          ))}
        </ul>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClear}>Xóa lịch sử</button>
      </div>
    </details>
  );
}
