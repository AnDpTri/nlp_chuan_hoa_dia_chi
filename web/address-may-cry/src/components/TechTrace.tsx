import React from 'react';
import { CopyButton } from './CopyButton';
import { IconDownload } from './Icons';
import './components.css';

/** Dấu vết kỹ thuật / JSON, thu gọn mặc định. */
export function TechTrace({ data, summary = 'Dấu vết kỹ thuật và JSON', fileName }: { data: unknown; summary?: string; fileName?: string }) {
  const json = JSON.stringify(data, null, 2);
  const download = () => {
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName || `dia_chi_chuan_hoa_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <details className="trace">
      <summary>{summary}</summary>
      <div className="trace-body">
        <div className="trace-actions">
          <CopyButton text={json} what="JSON" idleLabel="Chép JSON" doneLabel="Đã chép JSON" />
          <button type="button" className="copy-btn" onClick={download}>
            <IconDownload size={15} aria-hidden="true" /> Tải tệp .json
          </button>
        </div>
        <pre tabIndex={0} aria-label="Nội dung JSON">{json}</pre>
      </div>
    </details>
  );
}
