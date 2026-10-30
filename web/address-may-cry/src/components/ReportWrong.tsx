import React, { useState } from 'react';
import { sendFeedback } from '../shared/api';
import './components.css';

/** Nút "Báo kết quả sai": ghi lại câu nhập + ghi chú vào nhật ký phiên để phân tích lỗi thuật toán. */
export default function ReportWrong({ input, logId }: { input: string; logId?: string | null }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'saved' | 'off' | 'error'>('idle');

  const submit = async () => {
    setState('sending');
    try {
      const res = await sendFeedback(input, logId ?? null, note.trim());
      setState(res.saved ? 'saved' : 'off');
    } catch {
      setState('error');
    }
  };

  if (state === 'saved') {
    return <p role="status" className="report-msg">Đã ghi nhận báo sai. Cảm ơn bạn.</p>;
  }

  return (
    <div className="report">
      {!open ? (
        <button type="button" className="btn btn-sm report-open" onClick={() => setOpen(true)}>
          Báo kết quả sai
        </button>
      ) : (
        <form
          className="report-form"
          onSubmit={(e) => { e.preventDefault(); void submit(); }}
        >
          <label htmlFor="bao-sai-ghi-chu">
            Sai ở đâu? (không bắt buộc, ví dụ: “tỉnh bị bỏ qua”, “sai phường”)
          </label>
          <textarea
            id="bao-sai-ghi-chu"
            name="ghi_chu"
            autoComplete="off"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            maxLength={1000}
            placeholder="Ví dụ: sai phường, thiếu tỉnh…"
          />
          <div className="report-actions">
            <button type="submit" className="btn btn-primary btn-sm" disabled={state === 'sending'}>
              {state === 'sending' ? 'Đang gửi…' : 'Gửi báo sai'}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setOpen(false)}>
              Hủy
            </button>
            {state === 'off' && <span role="status" className="report-msg">Máy chủ đang tắt nhật ký (AMC_LOG≠1), chưa lưu được.</span>}
            {state === 'error' && <span role="alert" className="report-msg is-error">Gửi không được, hãy thử lại.</span>}
          </div>
        </form>
      )}
    </div>
  );
}
